"""Capture rendered Instagram comment evidence, without a comment API.

Captured blocks contain UI labels and are NOT automatically treated as original
comment text, top-level comments, or final research observations. Review required.
"""
import argparse
import asyncio
import json
import re
import time
from pathlib import Path

from .common import CAP, ROOT, now, targets


READ_BLOCKS = r"""({shortcode, cap}) => {
  const seen = new Set(), result = [];
  const idOf = a => {
    const m = new URL(a.href, location.href).pathname.match(/\/(?:p|reel)\/([^/]+)\/c\/(\d+)\/?$/);
    return m && m[1] === shortcode ? m[2] : null;
  };
  for (const a of document.querySelectorAll('a[href*="/c/"]')) {
    const id = idOf(a);
    if (!id || seen.has(id) || !a.getClientRects().length ||
        getComputedStyle(a).visibility === 'hidden' || a.closest('[aria-hidden="true"]')) continue;
    seen.add(id);
    let root = a.parentElement, best = root, boundary = 'minimal_parent_only';
    for (let depth=0; root && depth<12; depth++,root=root.parentElement) {
      const ids = new Set([...root.querySelectorAll('a[href*="/c/"]')].map(idOf).filter(Boolean));
      if (ids.size > 1) break;
      const text = root.innerText || '';
      best = root;
      if (/(^|\n)(Reply|回复|回覆)(\n|$)/i.test(text)) {
        boundary = 'single_permalink_block_with_reply_label'; break;
      }
    }
    const timeNode = a.querySelector('time') || best?.querySelector('time');
    result.push({comment_id: 'instagram_'+id, comment_permalink:a.href,
      visible_date_text:a.innerText, datetime_attribute:timeNode?.getAttribute('datetime') || null,
      visible_block_text:best?.innerText || a.innerText,
      extraction_boundary:boundary, comment_level:'unverified_requires_review'});
    if (result.length >= cap) break;
  }
  return result;
}"""

SCROLL_COMMENTS = r"""shortcode => {
  const anchor = [...document.querySelectorAll('a[href*="/c/"]')].find(a =>
    ['/p/','/reel/'].some(prefix => new URL(a.href,location.href).pathname.includes(prefix+shortcode+'/c/')) &&
    a.getClientRects().length && getComputedStyle(a).visibility !== 'hidden' && !a.closest('[aria-hidden="true"]'));
  if (!anchor) return false;
  for (let el=anchor.parentElement; el; el=el.parentElement) {
    const style = getComputedStyle(el);
    if (el.scrollHeight > el.clientHeight+40 && /auto|scroll/.test(style.overflowY)) {
      el.scrollBy(0,Math.max(200,el.clientHeight*0.7)); return true;
    }
  }
  return false;
}"""


async def ensure_comments_visible(page, shortcode, allow_manual=True, timeout=5000):
    """Open the labelled comment button on Reels before looking for comments."""
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    link = page.locator(f'a[href*="/{shortcode}/c/"]').first
    try:
        await link.wait_for(state="visible",timeout=timeout)
        return "already_visible"
    except PlaywrightTimeout:
        pass
    candidates=page.get_by_role("button",name=re.compile(r"^(Comment|Comments|评论|評論|留言)$",re.I))
    visible=[button for button in await candidates.all() if await button.is_visible()]
    if len(visible)==1:
        await visible[0].click()
        try:
            await link.wait_for(state="visible",timeout=timeout)
            return "opened_comment_panel"
        except PlaywrightTimeout:
            pass
    if allow_manual:
        print("Comment links are not visible yet. In the browser, open this post's comment bubble (not Reply), then return here. Do not like, follow or post anything.",flush=True)
        await asyncio.to_thread(input,"Once the comments are visible, press Enter here (Ctrl+C to stop): ")
        try:
            await link.wait_for(state="visible",timeout=timeout)
            return "manually_opened_comment_panel"
        except PlaywrightTimeout:
            pass
    return "comment_links_unavailable_not_verified_zero"


async def require_unobstructed_page(page):
    """Pause for an observed login/signup overlay; never read through it."""
    notice = page.get_by_text(re.compile(r"Never miss a post from|Sign up for Instagram to stay in the loop", re.I))
    if any([await item.is_visible() for item in await notice.all()]):
        print("A login/sign-up notice is covering this post. Please dismiss it using its visible close button, or log in yourself. No comments will be read through the notice.", flush=True)
        await asyncio.to_thread(input, "When the comment panel is unobstructed, press Enter here (Ctrl+C to stop): ")
        if any([await item.is_visible() for item in await notice.all()]):
            raise RuntimeError("Login/sign-up notice still obscures comments")


async def capture(rows, folder):
    from playwright.async_api import async_playwright
    folder.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=False)
        context = await browser.new_context(viewport={"width":1280, "height":900})
        try:
            page = await context.new_page()
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
            await asyncio.to_thread(input, "Log in yourself on Instagram in the new browser, then press Enter here. No username or password is requested in this terminal: ")
            for target in rows:
                shortcode = target["canonical_url"].rstrip("/").rsplit("/",1)[-1]
                if not re.fullmatch(r"[A-Za-z0-9_-]+",shortcode):
                    raise ValueError("Invalid shortcode")
                run_id = f"{shortcode}_{time.time_ns()}"
                evidence = dict(post_url=target["canonical_url"], post_id="instagram_"+shortcode,
                                collection_date=now(), collection_method="Visible browser DOM extraction; no comment API",
                                sort_order="Default displayed order; no sort controls changed; replies not expanded",
                                sample_role=target.get("sample_role","pending_review"),
                                selection_reason=target["selection_reason"],
                                status="pending", blocks=[], snapshots=[])
                path = folder / f"{run_id}.json"
                try:
                    await page.goto(target["canonical_url"],wait_until="domcontentloaded")
                    if any(part in page.url for part in ("/accounts/login", "/challenge/", "/checkpoint/")):
                        raise RuntimeError("Login or verification required; stop for manual handling")
                    evidence["comment_panel_action"] = await ensure_comments_visible(page,shortcode)
                    await require_unobstructed_page(page)
                    evidence["hk_relevance"] = target.get("hk_relevance", "unknown")
                    evidence["hk_evidence"] = target.get("hk_evidence", "unknown")
                    evidence["page_time_elements_for_review"] = await page.locator("time").evaluate_all(
                        "nodes => nodes.map(n => ({text:n.innerText,datetime:n.getAttribute('datetime'),link:n.closest('a')?.href || null}))")
                    seen, stalled = set(), 0
                    for step in range(5):
                        await require_unobstructed_page(page)
                        blocks = await page.evaluate(READ_BLOCKS, {"shortcode":shortcode,"cap":CAP})
                        screenshot = f"{run_id}_{step:02}.png"
                        await page.screenshot(path=str(folder / screenshot))
                        evidence["snapshots"].append(screenshot)
                        before = len(seen)
                        for block in blocks:
                            if block["comment_id"] in seen or len(seen) >= CAP:
                                continue
                            seen.add(block["comment_id"])
                            block.update(capture_position=len(seen), screenshot=screenshot)
                            evidence["blocks"].append(block)
                        path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
                        if len(seen)>=CAP or not blocks:
                            break
                        stalled = stalled+1 if len(seen)==before else 0
                        if stalled>=2 or not await page.evaluate(SCROLL_COMMENTS,shortcode):
                            break
                        await page.wait_for_timeout(1000)
                    # Freeze the first sample before scrolling to document each saved
                    # position. This evidence pass never adds replacement comments.
                    for block in evidence["blocks"]:
                        anchor = page.locator(f'a[href*="/{shortcode}/c/{block["comment_id"].removeprefix("instagram_")}/"]').first
                        try:
                            await anchor.scroll_into_view_if_needed(timeout=3000)
                            await anchor.evaluate("el => el.scrollIntoView({block:'center',inline:'nearest'})")
                            await require_unobstructed_page(page)
                            shot = f'{run_id}_position_{block["capture_position"]:02}.png'
                            await page.screenshot(path=str(folder / shot))
                            block["review_screenshot"] = shot
                            block["review_screenshot_note"] = "Scrolled to comment date link; inspect screenshot for complete text and hierarchy"
                            evidence["snapshots"].append(shot)
                        except Exception as exc:
                            block["review_screenshot_error"] = type(exc).__name__
                    evidence["status"] = "blocks_saved_manual_review_required" if seen else "no_comment_links_observed_not_verified_zero"
                    print(f"{shortcode}: saved {len(seen)} comment UI blocks; original text and top-level status require review.",flush=True)
                except Exception as exc:
                    evidence["status"]="interrupted_partial_evidence_only"
                    evidence["error_type"]=type(exc).__name__
                    raise
                finally:
                    path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f"Browser evidence saved to {folder}. No API or final comment coding was performed.")
        finally:
            await context.close()
            await browser.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets",default=str(ROOT/"private/instagram_browser_targets.csv"))
    parser.add_argument("--data-dir",default=str(ROOT/"data/instagram_browser"))
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    rows=targets(args.targets,"instagram")
    print(json.dumps({"posts":len(rows),"maximum_blocks_per_post":CAP,"mode":"browser-visible evidence, review required","live":args.live},ensure_ascii=False,indent=2))
    if not args.live:
        print("Dry run only; no browser opened.")
        return 0
    if not rows:
        parser.error("No selected posts")
    try:
        asyncio.run(capture(rows,Path(args.data_dir)))
    except (Exception,KeyboardInterrupt) as exc:
        print(f"Stopped: {type(exc).__name__}. Saved partial evidence is not a completed sample.")
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
