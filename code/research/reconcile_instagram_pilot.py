"""Reconcile live pilot evidence with earlier browser records; do not double count."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/instagram_pilot"
PREVIOUS = ROOT.parents[1] / "Outputs/SaSa_Section_2_2/support/analysis_data.json"
OUT = ROOT / "data/instagram_pilot_review"


def main():
    old = json.loads(PREVIOUS.read_text())
    posts = [json.loads(line) for line in (SOURCE / "posts.jsonl").read_text().splitlines()]
    comments = [json.loads(line) for line in (SOURCE / "comments.jsonl").read_text().splitlines()]
    browser = sorted([c for c in old["comments"] if c["post_id"] == "IG_P01"], key=lambda c: c["collection_rank"])
    assert len(comments) == len(browser) == 7
    assert all(c["post_id"] == "instagram_DBsunJ9SSmy" for c in comments)
    assert [c["text_original"] for c in comments] == [c["original_text"] for c in browser]
    crosswalk = []
    for c, b in zip(comments, browser):
        crosswalk.append(dict(platform_comment_id=c["comment_id"], previous_comment_id=b["comment_id"],
                              text_match=True, rank_match=c["sample_position"] == b["collection_rank"],
                              api_comment_date=c["comment_date"], api_comment_window=c["comment_window"],
                              prior_displayed_date=b["comment_date"], prior_included=b["included"],
                              creator_associated=b.get("creator_associated", False),
                              note="Featured-creator association from saved browser evidence is distinct from API is_creator, which checks only the publishing account." if b.get("creator_associated") else "",
                              browser_evidence=b["evidence_file"]))
    failed = [p for p in posts if p["access_status"] == "failed"]
    assert len(failed) == 1 and failed[0]["captured_comment_count"] is None
    audit = dict(source_posts_sha256=hashlib.sha256((SOURCE / "posts.jsonl").read_bytes()).hexdigest(),
                 source_comments_sha256=hashlib.sha256((SOURCE / "comments.jsonl").read_bytes()).hexdigest(),
                 successful_posts=1, failed_posts=1, saved_comments=7,
                 overlaps_prior_browser_comments=7, incremental_new_comments=0,
                 comment_windows=dict(Counter(c["comment_window"] for c in comments)),
                 substantive_historical_window_comments=sum(b["included"] is True and c["comment_window"] == "historical_season" for c, b in zip(comments, browser)),
                 crosswalk=crosswalk,
                 post_date_discrepancies=[dict(post_id="IG_P01", previous_date="2024-10-28",
                                               api_date=posts[0]["post_date"], status="Unresolved source discrepancy; retain both. Both are in October 2024. Do not silently overwrite the earlier source.")],
                 second_post_date_note="API timestamp 2024-10-01T23:27:38+00:00 corresponds to 2024-10-02 in Hong Kong, consistent with the earlier browser date; comments remain uncollected in this pilot.",
                 failure=dict(post_id=failed[0]["post_id"], metadata_read=True, complete_comment_sample_saved=False,
                              exception_type=failed[0]["error_type"], http_status="unknown",
                              reason="The retained log contains only the exception class. Cannot distinguish network failure, rate limiting or endpoint failure; no evidence establishes an account ban."),
                 order_note="Seven texts and their order match the previous saved browser capture for this post only. This does not validate ordering on all other posts.",
                 report_status="Original report and workbook preserved. This crosswalk is supplementary date/access evidence, not a new seven-comment sample.")
    OUT.mkdir(exist_ok=True)
    (OUT / "reconciliation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ["successful_posts", "failed_posts", "saved_comments", "incremental_new_comments", "comment_windows", "substantive_historical_window_comments"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
