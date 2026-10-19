"""Prepare two already documented posts for an Instagram code-access pilot."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1] / "Outputs/SaSa_Section_2_2/support/analysis_data.json"
DESTINATION = ROOT / "private/instagram_pilot_targets.csv"


def main():
    data = json.loads(SOURCE.read_text())
    rows = []
    for p in data["posts"]:
        if p["post_id"] not in {"IG_P01", "IG_P03"}:
            continue
        rows.append(dict(platform="instagram", url=p["url"], selected="yes",
                         selection_reason="Technical pilot: compare code access, exact comment dates and returned order against the prior browser capture. This is not a new independent post.",
                         hk_relevance=p["hk_relevance"], hk_evidence=p["hk_evidence"],
                         sample_role="technical_pilot_only", original_post_id=p["post_id"],
                         original_evidence_file=p["evidence_file"], previous_post_date=p["post_date"],
                         source_candidates_file=str(SOURCE)))
    assert len(rows) == 2
    with DESTINATION.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Prepared two known Instagram posts for a technical pilot; no live access claimed.")


if __name__ == "__main__":
    main()
