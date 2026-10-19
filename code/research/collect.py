"""Run from the workspace root: python -m research.collect --help.

Platform access is explicit (--live). Dry-run never imports platform libraries,
opens browsers, reads credentials, or sends requests. No cookie export or account pools.
"""
import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from itertools import islice
from urllib.parse import parse_qs, urlencode, urlparse

from .common import CAP, ROOT, Ledger, base_post, now, scope, screening_targets, targets, timestamp


async def instagram_browser_session():
    """Manual login in a fresh visible browser; session stays in process memory."""
    from playwright.async_api import async_playwright
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=False)
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
            await asyncio.to_thread(input, "Log in to Instagram yourself in the new browser. Complete verification manually, then press Enter here: ")
            cookies = {c["name"]: c["value"] for c in await context.cookies(["https://www.instagram.com"])}
            if not cookies.get("sessionid") or not cookies.get("csrftoken"):
                raise RuntimeError("Instagram browser login not confirmed; no comment requests started")
            return cookies, await page.evaluate("navigator.userAgent")
        finally:
            await context.close()
            await browser.close()


def collect_instagram(rows, ledger):
    sys.path.insert(0, str(ROOT / "instaloader"))
    import instaloader

    class ConservativeRateController(instaloader.RateController):
        def __init__(self, context):
            super().__init__(context)
            self.last_request = 0.0

        def wait_before_query(self, query_type):
            super().wait_before_query(query_type)
            time.sleep(max(0, 10 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()

        def handle_429(self, query_type):
            raise RuntimeError("Rate limit: stop the run; do not retry with another account")

    pending = []
    for target in rows:
        shortcode = urlparse(target["canonical_url"]).path.strip("/").split("/")[-1]
        post = base_post("instagram", shortcode, target)
        if not ledger.completed(post["post_id"]):
            pending.append((shortcode, post))
    if not pending:
        print("No pending Instagram posts. Previously completed samples were retained.")
        return
    username = input("Instagram username (not password; enter locally, not in chat): ").strip()
    if not username:
        raise ValueError("Instagram username is required")
    session_cookies, user_agent = asyncio.run(instagram_browser_session())
    loader = instaloader.Instaloader(
        user_agent=user_agent, quiet=True,
        download_pictures=False, download_videos=False, download_video_thumbnails=False,
        download_geotags=False, download_comments=False, save_metadata=False,
        max_connection_attempts=1, request_timeout=30,
        fatal_status_codes=[401, 403, 406, 429],
        rate_controller=ConservativeRateController,
    )
    # Upstream errors can include response details; print only the outer error type.
    loader.context.error = lambda *args, **kwargs: None
    try:
        # Public upstream in-memory API; never load/save a credential/session file.
        loader.load_session(username, session_cookies)
        verified_username = loader.test_login()
        if not verified_username:
            raise RuntimeError("Instagram session verification failed; stop without collecting comments")
        if verified_username.casefold() != username.casefold():
            raise RuntimeError("Browser account does not match the entered username; stop")
        for shortcode, post in pending:
            try:
                source = instaloader.Post.from_shortcode(loader.context, shortcode)
                post.update(title=source.caption or "", post_date=timestamp(source.date_utc), collection_date=now())
                creator_id = source.owner_id
                sample = []
                # No automatic traversal of .answers, profiles, followers, or media.
                for comment in islice(source.get_comments(), CAP):
                    sample.append({
                        "comment_id": f"instagram_{comment.id}",
                        "text_original": comment.text,
                        "comment_date": timestamp(comment.created_at_utc),
                        "anonymous_user": ledger.anonymous("instagram", comment.owner.userid),
                        "comment_level": "top_level", "parent_comment_id": "",
                        "is_creator": comment.owner.userid == creator_id,
                    })
                ledger.capture(post, sample)
                print(f"{post['post_id']}: captured {len(sample)} positions")
            except Exception as exc:
                ledger.failed(post, type(exc).__name__)
                raise
    finally:
        loader.close()
        session_cookies.clear()


async def collect_xhs(rows, ledger, keyword=None, page_number=1, screen_only=False):
    sys.path.insert(0, str(ROOT / "MediaCrawler"))
    import config
    from playwright.async_api import async_playwright
    from media_platform.xhs.client import XiaoHongShuClient
    from media_platform.xhs.field import SearchSortType
    from media_platform.xhs.help import get_search_id

    config.ENABLE_IP_PROXY = False
    config.ENABLE_GET_SUB_COMMENTS = False
    config.DISABLE_SSL_VERIFY = False
    # Do not use upstream start(), stealth scripts, CDP attachment, automatic login,
    # or creator crawling. This adapter uses one new visible, ephemeral context.
    logging.getLogger().setLevel(logging.CRITICAL)
    from tools import utils
    utils.logger.disabled = True

    class ResearchClient(XiaoHongShuClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.last_request = 0.0

        async def request(self, method, url, **kwargs):
            await asyncio.sleep(max(0, 10 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            return await super().request(method, url, **kwargs)

    pending = []
    for target in rows:
        note_id = urlparse(target["canonical_url"]).path.strip("/").split("/")[-1]
        post = base_post("xhs", note_id, target)
        done = ledger.metadata_completed(post["post_id"]) if screen_only else ledger.completed(post["post_id"])
        if not done:
            pending.append((target, note_id, post))
    if not keyword and not pending:
        print("No pending Xiaohongshu posts. Previously completed records were retained.")
        return
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=False)
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
            await asyncio.to_thread(input, "Log in yourself in the new browser. Complete any verification manually, then press Enter here: ")
            cookies = {c["name"]: c["value"] for c in await context.cookies(["https://www.xiaohongshu.com"])}
            if not cookies.get("web_session"):
                raise RuntimeError("Login not confirmed; no collection started")
            client = ResearchClient(
                headers={"Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
                         "User-Agent": await page.evaluate("navigator.userAgent"),
                         "Referer": "https://www.xiaohongshu.com/", "Origin": "https://www.xiaohongshu.com",
                         "Content-Type": "application/json;charset=UTF-8"},
                playwright_page=page, cookie_dict=cookies, timeout=30,
            )
            if keyword:
                # One page per invocation, preserving API rank. The keyword year is
                # a search term, never treated as a verified publication date.
                response = await client.get_note_by_keyword(keyword, get_search_id(), page=page_number,
                                                             page_size=20, sort=SearchSortType.GENERAL)
                if not isinstance(response.get("items"), list):
                    raise RuntimeError("Missing search items; not evidence of zero matching posts")
                candidates = []
                for rank, item in enumerate(response["items"], 1):
                    if item.get("model_type") in ("rec_query", "hot_query") or not item.get("id"):
                        continue
                    card = item.get("note_card") or {}
                    link = "https://www.xiaohongshu.com/explore/" + item["id"]
                    token = item.get("xsec_token")
                    if token:
                        link += "?" + urlencode({"xsec_token": token, "xsec_source": item.get("xsec_source") or "pc_search"})
                    candidates.append({"platform": "xhs", "url": link, "selected": "no",
                                       "selection_reason": "", "hk_relevance": "unknown", "hk_evidence": "",
                                       "title": card.get("display_title") or card.get("title") or "",
                                       "post_date": "unknown", "keyword": keyword, "search_page": page_number,
                                       "search_rank": rank, "search_sort": "general", "discovered_at": now()})
                # Access tokens in post links remain local; these files are git-ignored.
                path = ledger.folder / f"candidates_{time.time_ns()}.csv"
                fields = ["platform", "url", "selected", "selection_reason", "hk_relevance", "hk_evidence", "title", "post_date", "keyword", "search_page", "search_rank", "search_sort", "discovered_at"]
                with path.open("w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(candidates)
                ledger.event("search_completed", platform="xhs", keyword=keyword, page=page_number,
                             search_sort="general", candidates=len(candidates), file=path.name)
                print(f"Saved {len(candidates)} candidates to {path}. Review before selecting posts.")
                return
            for target, note_id, post in pending:
                try:
                    query = parse_qs(urlparse(target["url"]).query)
                    token = query.get("xsec_token", [""])[0]
                    if not token:
                        raise ValueError("Missing post-link access token; obtain the current link through visible search")
                    detail = await client.get_note_by_id(note_id, query.get("xsec_source", ["pc_search"])[0], token)
                    if not isinstance(detail, dict) or not detail:
                        raise RuntimeError("Post metadata unavailable; stop instead of assuming zero comments")
                    post.update(title=detail.get("title", ""), post_date=timestamp(detail.get("time")),
                                collection_date=now())
                    if screen_only:
                        # Keep only relevant post text and source dates, never profiles or media.
                        post.update(description_original=detail.get("desc", ""),
                                    source_publication_timestamp=detail.get("time"),
                                    source_update_timestamp=detail.get("last_update_time"),
                                    sort_order="not_applicable; metadata only; no comments requested")
                        ledger.screen(post)
                        print(f"{post['post_id']}: date={post['post_date']} window={scope(post['post_date'])}", flush=True)
                        continue
                    creator_id = (detail.get("user") or {}).get("user_id")
                    raw = await client.get_note_all_comments(note_id, token, max_count=CAP, crawl_interval=10)
                    sample = []
                    for comment in raw[:CAP]:
                        uid = (comment.get("user_info") or {}).get("user_id")
                        cid = comment.get("id")
                        if not cid:
                            raise ValueError("Missing comment ID")
                        parent = (comment.get("target_comment") or {}).get("id", "")
                        sample.append({"comment_id": f"xhs_{cid}", "text_original": comment.get("content"),
                                       "comment_date": timestamp(comment.get("create_time")),
                                       "anonymous_user": ledger.anonymous("xhs", uid),
                                       "comment_level": "reply" if parent else "top_level",
                                       "parent_comment_id": f"xhs_{parent}" if parent else "",
                                       "is_creator": uid == creator_id if uid and creator_id else "unknown"})
                    ledger.capture(post, sample)
                    print(f"{post['post_id']}: captured {len(sample)} positions")
                except Exception as exc:
                    ledger.failed(post, type(exc).__name__)
                    raise
            if screen_only:
                print(f"Metadata screening complete. Review {ledger.folder / 'posts.csv'}. No comments were requested.")
        finally:
            await context.close()
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=["xhs", "instagram"])
    parser.add_argument("--targets", default=str(ROOT / "private" / "targets.csv"))
    parser.add_argument("--data-dir", default=str(ROOT / "data"), help="Local output folder; use a separate folder for technical pilots")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--discover", metavar="KEYWORD", help="XHS only: retrieve one search page for review")
    mode.add_argument("--screen-candidates", metavar="CSV", help="XHS only: verify dates and post text for up to 20 candidates; no comments requested")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--live", action="store_true", help="Explicitly perform network access and local interactive login")
    args = parser.parse_args()
    if not 1 <= args.page <= 3:
        parser.error("Use a bounded search page between 1 and 3")
    if args.discover and args.platform != "xhs":
        parser.error("Instagram discovery requires browser search and reviewed post URLs")
    if args.screen_candidates and args.platform != "xhs":
        parser.error("Candidate metadata screening is currently Xiaohongshu only")
    rows = screening_targets(args.screen_candidates) if args.screen_candidates else ([] if args.discover else targets(args.targets, args.platform))
    plan = {"platform": args.platform, "selected_posts": 0 if args.screen_candidates else len(rows),
            "metadata_candidates": len(rows) if args.screen_candidates else 0,
            "comments_per_post_max": 0 if args.screen_candidates else CAP,
            "discovery_keyword": args.discover, "search_page": args.page, "live": args.live}
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.live:
        print("Dry run complete: no browser, login, or platform request was made.")
        return
    if not args.discover and not rows:
        parser.error("No reviewed targets selected; set selected=yes and record a selection_reason")
    ledger = Ledger(args.data_dir)
    try:
        if args.platform == "xhs":
            asyncio.run(collect_xhs(rows, ledger, args.discover, args.page, bool(args.screen_candidates)))
        else:
            collect_instagram(rows, ledger)
    except (Exception, KeyboardInterrupt) as exc:
        ledger.event("run_stopped", platform=args.platform, error_type=type(exc).__name__)
        # Never print exception payloads that might contain cookies or response profiles.
        print(f"Stopped: {type(exc).__name__}. Inspect access/login or dependencies before another run.", file=sys.stderr)
        return 1
    finally:
        ledger.export()
        ledger.db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
