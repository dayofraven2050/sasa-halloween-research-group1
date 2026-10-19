"""Audit browser blocks against previously reviewed comments; no double counting."""
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/instagram_browser/DAmZYfus0fa_1792433784908723000.json"
PREVIOUS=ROOT.parents[1]/"Outputs/SaSa_Section_2_2/support/analysis_data.json"
OUT=ROOT/"data/instagram_pilot_review/browser_reconciliation.json"


def main():
    data=json.loads(SOURCE.read_text())
    previous=json.loads(PREVIOUS.read_text())
    old=sorted([c for c in previous["comments"] if c["post_id"]=="IG_P03"],key=lambda c:c["collection_rank"])
    assert len(data["blocks"])==len(old)==15
    crosswalk=[]
    for block, comment in zip(data["blocks"],old):
        exact=comment["original_text"] in block["visible_block_text"]
        whitespace=" ".join(comment["original_text"].split()) in " ".join(block["visible_block_text"].split())
        assert exact or whitespace, comment["comment_id"]
        assert block["capture_position"]==comment["collection_rank"]
        crosswalk.append(dict(platform_comment_id=block["comment_id"],prior_comment_id=comment["comment_id"],
                              text_match="exact" if exact else "whitespace_normalized_only",
                              same_captured_rank=True,rendered_datetime_attribute=block["datetime_attribute"],
                              visible_date_label=block["visible_date_text"],prior_included=comment["included"],
                              original_text=comment["original_text"],
                              top_level_basis="Matches the same ranked comment in the previously reviewed top-level browser sample; current extraction alone does not establish nesting.",
                              previous_evidence_file=comment["evidence_file"]))
    result=dict(source=str(SOURCE),comments_matched=15,incremental_new_comments=0,
                date_year_counts=dict(Counter(b["datetime_attribute"][:4] for b in data["blocks"])),
                all_comment_datetime_attributes_in_october=True,
                previous_valid_comment_count=sum(c["included"] is True for c in old),
                crosswalk=crosswalk,
                newer_post_failure="Screenshot DeppGlOxgA4_1792433786924410000_00.png shows Reels full-screen player with the comment panel closed. Zero extracted blocks is not zero comments.",
                screenshot_limit="The screenshot shows only the viewport; the 15 blocks were rendered DOM text, including entries outside that viewport. The prior browser evidence supplies a separate textual cross-check.",
                original_report_status="Unchanged; exact-date supplement and source-ID crosswalk saved separately.")
    assert all(b["datetime_attribute"][5:7]=="10" for b in data["blocks"])
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("comments_matched","incremental_new_comments","date_year_counts","previous_valid_comment_count")},ensure_ascii=False))


if __name__=="__main__":
    main()
