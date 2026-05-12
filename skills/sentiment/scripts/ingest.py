"""Ingest the daily Fear & Greed Index from alternative.me.

One row per day, deduped by date (the API publishes once per day).
signal_type='fear_greed'. Source: "Fear & Greed Index" (source_type=macro).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func  # noqa: E402

from db import SessionLocal  # noqa: E402
from models import RawSignal, Source, SourceType  # noqa: E402

ENDPOINT = "https://api.alternative.me/fng/?limit=2"
TIMEOUT = 15


def fetch_payload() -> dict:
    r = requests.get(ENDPOINT, timeout=TIMEOUT, headers={"User-Agent": "crypto-tracker/0.1"})
    r.raise_for_status()
    return r.json()


def parse(payload: dict) -> dict:
    """Return one signal dict for the most recent point.

    Includes context (yesterday + last_week classification) when present.
    """
    rows = payload.get("data") or []
    if not rows:
        raise ValueError("no data in fng response")
    today = rows[0]
    value = int(today["value"])
    classification = today["value_classification"]
    timestamp = int(today["timestamp"])
    occurred_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    # The free /fng/ endpoint includes time_until_update; for yesterday +
    # last week we look at the next entry in the limit=2 batch and hint at
    # last_week via classification when available. To get last_week we'd
    # need a longer history, but the field is provided in some shape on
    # the limited endpoint:
    yesterday = rows[1] if len(rows) > 1 else None
    yesterday_class = yesterday.get("value_classification") if yesterday else None

    title = f"Fear & Greed: {value} ({classification})"
    if yesterday_class and yesterday_class != classification:
        title += f" — was {yesterday_class} yesterday"
    content = (
        f"The Crypto Fear & Greed Index reads {value} on a 0-100 scale, "
        f"classified as {classification}. The index aggregates volatility, "
        f"market momentum, social sentiment, dominance, and trend signals."
    )
    return {
        "signal_type": "fear_greed",
        "title": title,
        "content": content,
        "occurred_at": occurred_at,
        "raw_payload": {
            "value": value,
            "classification": classification,
            "value_yesterday": int(yesterday["value"]) if yesterday else None,
            "classification_yesterday": yesterday_class,
            "date": occurred_at.date().isoformat(),
        },
    }


def main() -> int:
    session = SessionLocal()
    try:
        source = (
            session.query(Source)
            .filter(
                Source.source_type == SourceType.macro,
                Source.name == "Fear & Greed Index",
            )
            .first()
        )
        if not source:
            print(
                "error: Fear & Greed Source row missing — run scripts/seed_sources.py first",
                file=sys.stderr,
            )
            return 1
        try:
            payload = fetch_payload()
            signal = parse(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"error: failed to fetch/parse Fear & Greed: {exc}", file=sys.stderr)
            return 2

        # Dedupe: skip if a fear_greed signal with the same date already exists.
        existing = (
            session.query(RawSignal.id)
            .filter(
                RawSignal.source_id == source.id,
                RawSignal.signal_type == "fear_greed",
                func.date(RawSignal.occurred_at) == signal["occurred_at"].date(),
            )
            .first()
        )
        if existing:
            print(
                f"skipped: fear_greed for {signal['occurred_at'].date()} already exists "
                f"(value={signal['raw_payload']['value']})"
            )
            return 0

        session.add(
            RawSignal(
                source_id=source.id,
                signal_type=signal["signal_type"],
                title=signal["title"],
                content=signal["content"],
                url="https://alternative.me/crypto/fear-and-greed-index/",
                raw_payload=signal["raw_payload"],
                occurred_at=signal["occurred_at"],
            )
        )
        session.commit()
        print(
            f"inserted: {signal['title']}  ({signal['occurred_at'].date()})"
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
