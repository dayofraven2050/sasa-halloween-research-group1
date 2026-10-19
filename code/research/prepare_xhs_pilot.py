"""Prepare a two-post technical pilot from the user's actual first search output.

This is a collector configuration CSV, not an analytical workbook. The search
source and original study target file are preserved. No source text is rewritten.
"""
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/candidates_1792430003773038000.csv"
DESTINATION = ROOT / "private/xhs_pilot_targets.csv"
PICKS = {
    "6aad0c710000000026008cfa": "Technical pilot only: compare code results with the previously browser-observed XHS_P01. Date and comment ordering need validation; not selected as a new substantive finding.",
    "6ad4603e000000001400fd57": "Technical pilot only: test a new, explicitly Hong Kong/Halloween-makeup titled post. Content type, date and comment accessibility remain unverified; not a final study sample.",
}


def main():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames) + ["sample_role", "source_candidates_file"]
        rows = list(reader)
    selected = []
    for row in rows:
        note_id = row["url"].split("?", 1)[0].rstrip("/").split("/")[-1]
        if note_id in PICKS:
            row.update(selected="yes", selection_reason=PICKS[note_id],
                       hk_relevance="title_mentions_Hong_Kong",
                       hk_evidence="Search-result title explicitly names Hong Kong; this does not establish commenter residence.",
                       sample_role="technical_pilot_only", source_candidates_file=SOURCE.name)
            selected.append(row)
    if len(selected) != 2:
        raise ValueError("Expected both observed pilot posts in the actual candidate file")
    DESTINATION.parent.mkdir(exist_ok=True)
    with DESTINATION.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
    print("Two technical-pilot targets prepared; original search candidates unchanged.")


if __name__ == "__main__":
    main()
