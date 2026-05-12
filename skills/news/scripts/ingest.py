"""Ingest active news_rss sources into raw_signals.

For each Source where is_active=true and source_type='news_rss':
- Fetch + parse via feedparser
- Skip entries without published_parsed
- Skip entries whose url already exists in raw_signals (UNIQUE partial index
  also enforces this at the DB level)
- Insert new entries with signal_type='news_article'

One feed failing does not abort the run. Exits 0 even on partial failures so a
scheduler treats it as success; failures are visible in the stdout summary.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal  # noqa: E402
from models import RawSignal, Source, SourceType  # noqa: E402


def struct_time_to_dt(t: time.struct_time) -> datetime:
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)


def entry_to_json_safe(entry: Any) -> dict:
    """feedparser entries contain time.struct_time and FeedParserDict objects;
    flatten to a plain JSON-serializable dict."""

    def coerce(v: Any) -> Any:
        if isinstance(v, time.struct_time):
            return struct_time_to_dt(v).isoformat()
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        if isinstance(v, dict):
            return {k: coerce(val) for k, val in v.items()}
        if isinstance(v, list):
            return [coerce(x) for x in v]
        return str(v)

    return {k: coerce(v) for k, v in dict(entry).items()}


def ingest_source(session, source: Source) -> dict:
    stats = {"fetched": 0, "new": 0, "skipped_no_date": 0, "skipped_dup": 0}
    parsed = feedparser.parse(source.url)
    stats["fetched"] = len(parsed.entries)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError(f"feedparser failed: {parsed.bozo_exception}")

    for entry in parsed.entries:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published:
            stats["skipped_no_date"] += 1
            continue
        url = entry.get("link")
        if not url:
            stats["skipped_no_date"] += 1
            continue
        existing = (
            session.query(RawSignal.id).filter(RawSignal.url == url).first()
        )
        if existing:
            stats["skipped_dup"] += 1
            continue

        signal = RawSignal(
            source_id=source.id,
            signal_type="news_article",
            title=entry.get("title", "(no title)"),
            content=entry.get("summary") or entry.get("description") or "",
            url=url,
            raw_payload=entry_to_json_safe(entry),
            occurred_at=struct_time_to_dt(published),
        )
        session.add(signal)
        stats["new"] += 1

    session.commit()
    return stats


def main() -> int:
    session = SessionLocal()
    rows: list[tuple[str, dict | str]] = []
    try:
        sources = (
            session.query(Source)
            .filter(
                Source.is_active.is_(True),
                Source.source_type == SourceType.news_rss,
            )
            .order_by(Source.name)
            .all()
        )
        for src in sources:
            try:
                stats = ingest_source(session, src)
                rows.append((src.name, stats))
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                rows.append((src.name, f"ERROR: {exc}"))
    finally:
        session.close()

    print(f"{'source':<12} {'fetched':>8} {'new':>5} {'dup':>5} {'no-date':>8}")
    print("-" * 44)
    total_new = 0
    for name, stats in rows:
        if isinstance(stats, str):
            print(f"{name:<12} {stats}")
            continue
        print(
            f"{name:<12} {stats['fetched']:>8} {stats['new']:>5} "
            f"{stats['skipped_dup']:>5} {stats['skipped_no_date']:>8}"
        )
        total_new += stats["new"]
    print("-" * 44)
    print(f"total new rows: {total_new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
