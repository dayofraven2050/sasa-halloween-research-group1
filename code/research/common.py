"""Local evidence ledger. Uses only the Python standard library."""
import csv
import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CAP = 15
HK = ZoneInfo("Asia/Hong_Kong")


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    if value is None or value == "" or value == "unknown":
        return "unknown"
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    else:
        try:
            number = float(value)
            dt = datetime.fromtimestamp(number / 1000 if number > 100_000_000_000 else number, timezone.utc)
        except (ValueError, TypeError, OverflowError, OSError):
            return "unknown"
    return dt.astimezone(timezone.utc).isoformat()


def scope(iso_date):
    try:
        dt = datetime.fromisoformat(iso_date)
        if dt.tzinfo:
            dt = dt.astimezone(HK)
    except (TypeError, ValueError):
        return "unknown"
    if dt.year in (2024, 2025) and dt.month in (9, 10):
        return "historical_season"
    if dt.year == 2026:
        return "2026_extension"
    return "outside_window"


def canonical(platform, url):
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if platform == "xhs" and parsed.hostname in {"xiaohongshu.com", "www.xiaohongshu.com"}:
        if len(parts) == 2 and parts[0] == "explore":
            return f"https://www.xiaohongshu.com/explore/{parts[1]}"
        if len(parts) == 3 and parts[:2] == ["discovery", "item"]:
            return f"https://www.xiaohongshu.com/explore/{parts[2]}"
    if platform == "instagram" and parsed.hostname in {"instagram.com", "www.instagram.com"}:
        if len(parts) == 2 and parts[0] in {"p", "reel"}:
            return f"https://www.instagram.com/{parts[0]}/{parts[1]}/"
    raise ValueError(f"Unsupported post URL for {platform}")


def targets(path, platform):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("platform") == platform and r.get("selected", "").lower() == "yes"]
    seen, selected = set(), []
    for row in rows:
        url = canonical(platform, row["url"])
        if not row.get("selection_reason", "").strip():
            raise ValueError("Every selected post needs a selection_reason")
        if url not in seen:
            row["canonical_url"] = url
            selected.append(row)
            seen.add(url)
    if len(selected) > 12:
        raise ValueError("This study targets at most 12 selected posts per platform")
    return selected


def screening_targets(path):
    """Bounded metadata review of search results; does not select research posts."""
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    seen, candidates = set(), []
    for row in rows:
        if row.get("platform") != "xhs":
            raise ValueError("Metadata screening accepts Xiaohongshu candidates only")
        url = canonical("xhs", row["url"])
        if url in seen:
            continue
        seen.add(url)
        candidates.append(dict(row, canonical_url=url,
                               selection_reason="Metadata screening only; relevance and final sample selection remain pending.",
                               sample_role="candidate_metadata_only",
                               source_candidates_file=Path(path).name))
    if len(candidates) > 20:
        raise ValueError("Screen at most one 20-post candidate batch per run")
    return candidates


class Ledger:
    def __init__(self, folder=None):
        self.folder = Path(folder or ROOT / "data")
        self.folder.mkdir(parents=True, exist_ok=True)
        key_path = self.folder / ".anon_key"
        if not key_path.exists():
            key_path.write_bytes(secrets.token_bytes(32))
            key_path.chmod(0o600)
        self.key = key_path.read_bytes()
        self.db = sqlite3.connect(self.folder / "research.sqlite")
        self.db.execute("CREATE TABLE IF NOT EXISTS posts (post_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS comments (comment_id TEXT PRIMARY KEY, post_id TEXT, payload TEXT NOT NULL)")
        self.db.commit()

    def anonymous(self, platform, user_id):
        if user_id is None or user_id == "":
            return "unknown"
        return platform + "_U_" + hmac.new(self.key, f"{platform}:{user_id}".encode(), hashlib.sha256).hexdigest()[:16]

    def post(self, post_id):
        row = self.db.execute("SELECT payload FROM posts WHERE post_id=?", (post_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def completed(self, post_id):
        return (self.post(post_id) or {}).get("access_status") == "sample_captured"

    def metadata_completed(self, post_id):
        return (self.post(post_id) or {}).get("access_status") in {"metadata_screened", "sample_captured"}

    def screen(self, post):
        if self.completed(post["post_id"]):
            return
        # No comment request was made. NULL is not a finding of zero comments.
        saved = dict(post, access_status="metadata_screened", captured_comment_count=None,
                     inspected_positions=None, post_window=scope(post.get("post_date", "unknown")))
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO posts VALUES (?,?)", (post["post_id"], json.dumps(saved, ensure_ascii=False)))
        self.event("metadata_screened", post_id=post["post_id"], post_window=saved["post_window"])

    def event(self, event, **data):
        with (self.folder / "collection_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "event": event, **data}, ensure_ascii=False) + "\n")

    def capture(self, post, comments):
        # Limit before deduplication: never scroll farther to replace invalid or duplicate rows.
        sample = list(islice(comments, CAP))
        unique = {}
        for rank, raw in enumerate(sample, 1):
            row = dict(raw)
            if not row.get("comment_id"):
                raise ValueError("Missing stable comment ID; sample requires review")
            if not isinstance(row.get("text_original"), str):
                raise ValueError("Missing original comment text")
            row.update(post_id=post["post_id"], platform=post["platform"], post_url=post["url"],
                       collection_date=post["collection_date"], collection_method=post["collection_method"],
                       sort_order=post["sort_order"], sample_position=rank,
                       inclusion_status="pending_manual_review", themes="", evidence_excerpt="")
            row["comment_window"] = scope(row.get("comment_date", "unknown"))
            unique.setdefault(row["comment_id"], row)
        saved = dict(post, access_status="sample_captured", captured_comment_count=len(unique),
                     inspected_positions=len(sample), duplicate_count=len(sample)-len(unique),
                     post_window=scope(post.get("post_date", "unknown")))
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO posts VALUES (?,?)", (post["post_id"], json.dumps(saved, ensure_ascii=False)))
            self.db.execute("DELETE FROM comments WHERE post_id=?", (post["post_id"],))
            for cid, row in unique.items():
                self.db.execute("INSERT OR REPLACE INTO comments VALUES (?,?,?)", (cid, post["post_id"], json.dumps(row, ensure_ascii=False)))
        self.event("sample_captured", post_id=post["post_id"], count=len(unique))

    def failed(self, post, reason):
        # NULL count explicitly differs from a successful empty list (zero).
        saved = dict(post, access_status="failed", captured_comment_count=None, error_type=reason)
        if not self.completed(post["post_id"]):
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO posts VALUES (?,?)", (post["post_id"], json.dumps(saved, ensure_ascii=False)))
        self.event("collection_stopped", post_id=post["post_id"], error_type=reason)

    def export(self):
        for table in ("posts", "comments"):
            rows = [json.loads(r[0]) for r in self.db.execute(f"SELECT payload FROM {table} ORDER BY rowid")]
            # JSONL preserves original text and is the canonical export. CSV is a convenience view.
            (self.folder / f"{table}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
            if rows:
                fields = list(dict.fromkeys(k for r in rows for k in r))
                with (self.folder / f"{table}.csv").open("w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)


def base_post(platform, platform_id, target):
    return {"post_id": f"{platform}_{platform_id}", "platform": platform,
            "url": target["canonical_url"], "collection_date": now(),
            "collection_method": "Code: upstream library adapter; not a browser transcription",
            "sort_order": "API returned order; browser-visible order equivalence unverified",
            "hk_relevance": target.get("hk_relevance") or "unknown",
            "hk_evidence": target.get("hk_evidence") or "unknown",
            "selection_reason": target["selection_reason"], "post_date": "unknown",
            "sample_role": target.get("sample_role") or "research_candidate_pending_review",
            **{key: target[key] for key in ("source_candidates_file", "source_metadata_file", "keyword", "search_page", "search_rank", "search_sort", "discovered_at") if key in target}}
