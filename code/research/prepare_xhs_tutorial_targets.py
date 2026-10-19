"""Prepare six reviewed 2026 extension posts; not a final analytical sample.

Selection uses actual post metadata, before seeing comments or engagement counts.
The original candidate file and metadata screening outputs remain unchanged.
"""
import csv
import hashlib
import json
from pathlib import Path

from .common import canonical, scope, targets

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/candidates_1792430409560029000.csv"
METADATA = ROOT / "data/xhs_tutorial_screening/posts.jsonl"
DESTINATION = ROOT / "private/xhs_tutorial_2026_targets.csv"
MANIFEST = ROOT / "private/xhs_tutorial_2026_selection.json"
PICKS = {
    "6aca2fd1000000001a025c97": "Everyday-makeup adaptation: caption describes a normal makeup base, stronger blush and eyeliner doodles. Retain possible existing-product substitution; no comment outcome assumed.",
    "6ac39d3b000000000d0281d0": "Special-effects wound tutorial with cosplay tags and a durability claim in the title. Examine practical questions; no product purchase or difficulty inferred from the title.",
    "6ad5f73a000000002a026cd0": "Gothic vampire tutorial: adds a distinct character/style to the tutorial sample. Caption supplies no verified Hong Kong connection or purchase evidence.",
    "6ad34887000000001801bdc1": "Quick spiderweb tutorial: title claims a cotton swab is sufficient as a drawing tool. Examine time/equipment questions; the title does not prove no other cosmetics are needed.",
    "6aba764c000000001b01c08b": "Adam-themed imitation makeup with cosplay/Halloween tags: adds character imitation and an earlier September post. Comment reactions remain unknown.",
    "6ad52f2a0000000029009b2b": "Doll special-effects tutorial: caption describes effort, clay application and a retry. Adds an effort-intensive example; creator experience is not consumer-comment evidence.",
}


def main():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    metadata_hash = hashlib.sha256(METADATA.read_bytes()).hexdigest()
    records = {r["post_id"]: r for r in map(json.loads, METADATA.read_text(encoding="utf-8").splitlines())}
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames)
        candidates = list(reader)
    extra = ["sample_role", "source_candidates_file", "source_metadata_file"]
    selected = []
    for row in candidates:
        note_id = canonical("xhs", row["url"]).rsplit("/", 1)[-1]
        if note_id not in PICKS:
            continue
        metadata = records[f"xhs_{note_id}"]
        if metadata["access_status"] != "metadata_screened" or scope(metadata["post_date"]) != "2026_extension":
            raise ValueError("Expected an actually screened 2026 extension post")
        row.update(selected="yes", selection_reason=PICKS[note_id],
                   post_date=metadata["post_date"],
                   hk_relevance="general_reference_hk_unverified",
                   hk_evidence="Reviewed title/caption provide no explicit Hong Kong event or place. Creator profiles were not reviewed; commenter residence is unknown.",
                   sample_role="2026_extension_pending_comment_review",
                   source_candidates_file=str(SOURCE.relative_to(ROOT)),
                   source_metadata_file=str(METADATA.relative_to(ROOT)))
        selected.append(row)
    if len(selected) != 6:
        raise ValueError("Expected all six reviewed candidates")
    DESTINATION.parent.mkdir(exist_ok=True)
    with DESTINATION.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields + extra)
        writer.writeheader()
        writer.writerows(selected)
    manifest = {
        "source_sha256": source_hash, "metadata_sha256": metadata_hash,
        "screened_candidates": len(records), "historical_window_posts": sum(scope(r["post_date"]) == "historical_season" for r in records.values()),
        "selected_for_comment_collection": len(selected), "maximum_comment_positions": 90,
        "selection_basis": "Purposive topic variation among this one query's screened results; comments and engagement counts were not used to select posts.",
        "status": "Prepared only; no new comment capture is claimed by this manifest.",
        "limitations": ["All six are 2026 extension posts, not 2024/2025 historical samples.",
                        "All six are general reference with Hong Kong relevance unverified.",
                        "Tutorials alone do not cover all study topics; product questions and purchasing concerns are not yet observed.",
                        "API comment order remains unverified against browser-visible order.",
                        "No final analytical inclusion or theme coding before reading captured comments."],
        "selected_posts": [{"post_id": "xhs_" + canonical("xhs", r["url"]).rsplit("/", 1)[-1],
                            "title": r["title"], "post_date": r["post_date"], "reason": r["selection_reason"]} for r in selected],
    }
    with MANIFEST.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    assert hashlib.sha256(METADATA.read_bytes()).hexdigest() == metadata_hash
    assert len(targets(DESTINATION, "xhs")) == 6
    print("Prepared six 2026 extension targets; original data unchanged; comment collection pending.")


if __name__ == "__main__":
    main()
