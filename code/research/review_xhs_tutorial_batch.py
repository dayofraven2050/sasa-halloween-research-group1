"""Reproduce individually reviewed coding of the captured six-post extension.

No network calls. Source JSONL is untouched. Decisions below were made after
reading each saved original, not by automatic keyword or sentiment matching.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/xhs_research"
OUT = ROOT / "data/xhs_research_review"
PREVIOUS = ROOT.parents[1] / "Outputs/SaSa_Section_2_2/support/analysis_data.json"


def d(status, themes="", subtype="", response="other", note=""):
    return dict(inclusion_status=status, themes=themes.split(), theme_subtypes=subtype.split(),
                engagement_type=response, review_notes=note)


# Entries follow the captured API positions, including excluded/unclear positions.
DECISIONS = {
    "xhs_6aca2fd1000000001a025c97": [
        d("valid", "T8", "accessory_contact_lenses", "information_request", "Contact lenses, not a cosmetic purchase."),
        d("valid", "T8", "accessory_contact_lenses", "information_request"),
        d("valid", "T3", "eyeliner", "information_request", "球 is interpreted as 求 in this product enquiry."),
        d("valid", "T1 T3", "lip_colour", "information_request_and_effect_praise"),
        d("valid", "T8", "unspecified_pen_or_tool", "information_request", "The comment says pen; its cosmetic category is unconfirmed without video context."),
        d("valid", "T1", "general_look_praise", "effect_praise", "Praise includes the presentation/gesture; not purchase evidence."),
        d("valid", "T3", "white_eyeliner", "information_request"),
        d("excluded", note="Bare numeral; no substantive research content."),
        d("excluded", note="Mention only; no substantive research content. Display text is anonymised separately."),
        d("valid", "T1", "general_look_praise", "effect_praise"),
    ],
    "xhs_6ac39d3b000000000d0281d0": [
        d("valid", "T1 T2", "additional_tutorial_request", "information_request_and_effect_praise"),
        d("valid", "T2 T8", "removal_method removal_discomfort", "information_request", "A removal/pain concern, not evidence the product causes pain."),
        d("valid", "T8", "special_effects_material", "information_request", "Liquid latex material enquiry; separate from conventional cosmetic/shade questions."),
        d("valid", "T1", "general_result_or_skill_praise", "effect_praise"),
        d("valid", response="tutorial_gratitude", note="On-topic thanks; does not demonstrate learning, purchase, or a specific unmet need."),
        d("valid", "T1", "realistic_special_effect", "effect_praise"),
        d("valid", "T1", "realistic_special_effect", "effect_praise"),
        d("valid", "T1", "general_result_or_skill_praise", "effect_praise"),
        d("valid", "T8", "special_effects_material", "information_request", "Same author/text as position 3, 55 seconds later, with a different source comment ID. Retained as a separate posting, flagged in sensitivity analysis."),
        d("valid", "T1", "realistic_special_effect", "effect_praise", "Phantom-pain reaction is praise of a visual effect, not a report of product injury."),
        d("valid", "T1", "realistic_special_effect", "effect_praise", "Frightening is complimentary in this Halloween context."),
        d("valid", "T1", "character_recognition", "character_recognition"),
        d("valid", "T1", "realistic_special_effect", "effect_praise"),
        d("valid", "T1", "character_and_horror_effect", "effect_praise"),
        d("valid", "T1 T8", "family_makeup_interest", "stated_makeup_use_intention", "One wish to apply a look to a daughter; no purchase commitment or verified demand for paid children's services."),
    ],
    "xhs_6ad5f73a000000002a026cd0": [],
    "xhs_6ad34887000000001801bdc1": [
        d("valid", "T3 T7", "dark_blush product_link", "information_request", "Asking for a link is sourcing information, not an explicit commitment to buy."),
        d("valid", "T2", "self_reported_learning", "tutorial_feedback", "Self-reported learning, without a verified recreation or purchase."),
    ],
    "xhs_6aba764c000000001b01c08b": [
        d("unclear", note="Familiar-looking glasses; insufficient context to identify the reference or a makeup need."),
        d("valid", "T1", "general_look_quality", "effect_praise"),
        d("valid", "T1", "character_resemblance", "effect_praise"),
        d("valid", "T2", "joking_time_comment", "tutorial_time_comment", "A joke about it becoming dark while gluing brows. Signals attention to a step/time, not measured duration or confirmed consumer burden."),
        d("unclear", note="Performance-related remark; its relevance to makeup cannot be established."),
        d("valid", "T1", "general_result_or_skill_praise", "effect_praise"),
        d("valid", "T1", "character_resemblance", "effect_praise"),
        d("valid", "T2", "self_deprecating_skill_comment", "tutorial_difficulty_comment", "Where can I get the hands is a skill-related joke, not a literal product request."),
        d("unclear", note="Again lacks a clear referent or interpretable stance."),
        d("unclear", note="能cos嘛 does not specify the intended role or whether this is a request to the creator or for permission."),
        d("unclear", note="May praise the creator's natural resemblance rather than a reproducible cosmetic effect."),
        d("unclear", note="Exclamation/emoji without a sufficiently clear meaning."),
        d("valid", "T1", "character_resemblance", "effect_praise"),
        d("excluded", note="Bare numeral; no substantive research content."),
        d("excluded", note="Bare numeral; no substantive research content."),
    ],
    "xhs_6ad52f2a0000000029009b2b": [
        d("valid", "T1", "general_result_or_skill_praise", "effect_praise"),
        d("unclear", note="WOW with emoji is an ambiguous exclamation; no theme forced."),
        d("excluded", note="Emoji only; no substantive interpretable text."),
    ],
}


def main():
    posts = [json.loads(x) for x in (SOURCE / "posts.jsonl").read_text().splitlines()]
    comments = [json.loads(x) for x in (SOURCE / "comments.jsonl").read_text().splitlines()]
    assert set(DECISIONS) == {p["post_id"] for p in posts}
    assert len(comments) == len({c["comment_id"] for c in comments}) == 45
    raw_hash = hashlib.sha256((SOURCE / "comments.jsonl").read_bytes()).hexdigest()
    grouped = defaultdict(list)
    for c in comments:
        grouped[c["post_id"]].append(c)
    for p in posts:
        assert len(grouped[p["post_id"]]) == p["captured_comment_count"] == len(DECISIONS[p["post_id"]])
        assert p["post_window"] == "2026_extension"
        assert p["duplicate_count"] == 0
    old = json.loads(PREVIOUS.read_text())
    old_urls = {p["url"].split("?", 1)[0].rstrip("/") for p in old["posts"]}
    assert all(p["url"].rstrip("/") not in old_urls for p in posts)
    reviewed = []
    same_author_text = defaultdict(list)
    for c in comments:
        assert c["comment_level"] == "top_level" and c["is_creator"] is False
        assert c["comment_window"] == "2026_extension"
        decision = DECISIONS[c["post_id"]][c["sample_position"] - 1]
        row = dict(c, **{k: v for k, v in decision.items() if k not in c})
        row.update(decision)
        row.update(evidence_excerpt=c["text_original"] if decision["inclusion_status"] == "valid" else "",
                   display_text="@[mentioned account]" if c["text_original"].startswith("@") else c["text_original"],
                   purchase_evidence="No explicit purchase intention or self-reported completed purchase in this comment.",
                   review_status="Codex individual text review against saved API original; browser context/order unverified.",
                   analysis_role="2026 extension; general reference; not Hong Kong population evidence",
                   source_jsonl=str(SOURCE / "comments.jsonl"), source_line=comments.index(c) + 1)
        reviewed.append(row)
        same_author_text[(c["post_id"], c["anonymous_user"], c["text_original"])].append(c["comment_id"])
    repeated = [ids for (post, user, text), ids in same_author_text.items() if user != "unknown" and len(ids) > 1]
    repeated_later = {cid for ids in repeated for cid in ids[1:]}
    for row in reviewed:
        row["repeated_same_user_text"] = next((";".join(ids) for ids in repeated if row["comment_id"] in ids), "")
        row["sensitivity_exclude_repeated_posting"] = row["comment_id"] in repeated_later
    valid = [r for r in reviewed if r["inclusion_status"] == "valid"]
    status = Counter(r["inclusion_status"] for r in reviewed)
    theme_counts = {f"T{i}": {"comments": sum(f"T{i}" in r["themes"] for r in valid),
                                "posts": len({r["post_id"] for r in valid if f"T{i}" in r["themes"]}),
                                "comment_denominator": len(valid), "all_selected_post_denominator": len(posts),
                                "nonempty_post_denominator": len(grouped) - sum(not grouped[p["post_id"]] for p in posts)} for i in range(1, 9)}
    summary = dict(reviewed_at=datetime.now(timezone.utc).isoformat(),
                   source_comments_sha256=raw_hash, selected_posts=6, posts_with_comments=5,
                   raw_comments=45, unique_platform_comment_ids=45, original_capture_duplicates=0,
                   all_top_level=True, all_comment_dates="2026 September/October; extension only",
                   status_counts=dict(status), themes=theme_counts,
                   explicit_purchase_intention=0, self_reported_purchase=0,
                   repeated_same_user_text_groups=repeated,
                   valid_if_collapsing_repeated_same_user_text=sum(r["comment_id"] not in repeated_later for r in valid),
                   historical_2024_2025_posts=0, confirmed_hk_posts=0,
                   old_report_overlap_posts=0,
                   limitations=["API return order is not verified against browser-visible order; do not silently merge with original browser-order statistics.",
                                "Six purposively chosen tutorials; comments are clustered within posts, not independent sampled consumers.",
                                "Post captions were used for selection/context, never counted as comments.",
                                "A verified empty response on one post means zero captured comments, not proof the post has no comments anywhere.",
                                "No observations of price, waste/reuse or existing-product substitution in these comments; their absence does not show these concerns are absent in the market.",
                                "The existing report and workbook are unchanged; merging remains pending."],
                   codebook_source=str(PREVIOUS),
                   codebook_additions={"special_effects_material": "Liquid latex enquiries kept under T8, distinct from ordinary makeup items under T3.",
                                       "removal_discomfort": "Questions about removal and potential pain, not verified adverse effects.",
                                       "family_makeup_interest": "A stated wish to apply makeup to a child, not demand for a paid service.",
                                       "joking_time_comment": "Quoted humorous time reference; never interpreted as measured time or frequency."})
    assert status == Counter(valid=33, excluded=5, unclear=7)
    assert summary["valid_if_collapsing_repeated_same_user_text"] == 32
    OUT.mkdir(exist_ok=True)
    (OUT / "reviewed_comments.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reviewed))
    with (OUT / "reviewed_comments.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(reviewed[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for k, v in r.items()} for r in reviewed)
    (OUT / "review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    assert hashlib.sha256((SOURCE / "comments.jsonl").read_bytes()).hexdigest() == raw_hash
    print(json.dumps({"posts": 6, "raw_comments": 45, "reviewed": dict(status), "themes": theme_counts,
                      "repeat_sensitivity_valid": 32, "output": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
