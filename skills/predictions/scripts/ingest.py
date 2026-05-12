"""Ingest top crypto-relevant Polymarket prediction markets into raw_signals.

signal_type='prediction_market'. We store the full snapshot as a fresh
row each time the dedupe window expires (default 6h) so the table
becomes a time series of probability movements per market.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import desc  # noqa: E402

from db import SessionLocal  # noqa: E402
from models import RawSignal, Source, SourceType  # noqa: E402

GAMMA = "https://gamma-api.polymarket.com"
TIMEOUT = 25
DEDUPE_HOURS = 6
TOP_N = 30
FETCH_LIMIT = 200  # broader pool so we can filter and still hit 30
MIN_24H_VOLUME = 50  # skip near-dead markets

# Loosened keyword list — we want broad signal coverage, not just the
# tight set the dashboard uses for display.
CRYPTO_KEYWORDS = [
    "bitcoin", "btc",
    "ethereum", "eth",
    "solana", "sol",
    "crypto", "blockchain",
    "sec ", "etf",
    "stablecoin", "usdc", "usdt", "tether",
    "ripple", "xrp",
    "dogecoin", "doge",
    "coinbase", "binance", "kraken",
    "defi", "tokeniz",
    "halving", "halvening",
    "miner", "mining",
    "polymarket",
    "ftx", "sbf",
    "tether",
    "mempool",
    "fed ", "powell", "rate cut", "rate hike", "interest rate",
    "cbdc",
]


def looks_crypto(question: str) -> bool:
    if not question:
        return False
    q = question.lower()
    return any(kw in q for kw in CRYPTO_KEYWORDS)


def parse_yes_prob(prices_json: str | None) -> float | None:
    if not prices_json:
        return None
    try:
        arr = json.loads(prices_json)
        v = float(arr[0])
        if 0.0 <= v <= 1.0:
            return v
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    return None


def fetch_markets() -> list[dict]:
    url = (
        f"{GAMMA}/markets?active=true&closed=false"
        f"&order=volume24hr&ascending=false&limit={FETCH_LIMIT}"
    )
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "crypto-tracker/0.1"})
    r.raise_for_status()
    return r.json()


def _f(v) -> float | None:
    """Polymarket returns most numerics as strings — coerce safely."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_signal(m: dict) -> dict | None:
    question = m.get("question") or ""
    if not looks_crypto(question):
        return None
    vol = _f(m.get("volume24hr")) or 0
    total_vol = _f(m.get("volume")) or 0
    if vol < MIN_24H_VOLUME:
        return None
    yes = parse_yes_prob(m.get("outcomePrices"))
    if yes is None:
        return None
    no = 1.0 - yes
    yes_pct = round(yes * 100, 1)

    # Polymarket sometimes returns a 1d/24h price-change-ish field;
    # surface what's there but tolerate absence.
    change_24h_raw = m.get("oneDayPriceChange")
    change_pp_24h: float | None = None
    if isinstance(change_24h_raw, (int, float)):
        change_pp_24h = change_24h_raw * 100  # convert prob delta to percentage points

    end_date = m.get("endDate")
    days_to_resolution: int | None = None
    if end_date:
        try:
            d = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            days_to_resolution = max(0, (d.date() - datetime.now(timezone.utc).date()).days)
        except (ValueError, AttributeError):
            days_to_resolution = None

    change_str = ""
    if change_pp_24h is not None:
        sign = "+" if change_pp_24h >= 0 else ""
        change_str = f" ({sign}{change_pp_24h:.1f}pp 24h)"
    title = f"{question} — {yes_pct:.1f}% YES{change_str}"

    content = (
        f"Polymarket: {question}\n"
        f"YES probability: {yes_pct:.1f}% (NO: {no*100:.1f}%). "
        f"24h volume: ${vol:,.0f}. "
        f"Total volume: ${total_vol:,.0f}. "
        + (f"Resolves in ~{days_to_resolution} days. " if days_to_resolution is not None else "")
        + (f"24h probability change: {change_pp_24h:+.1f}pp." if change_pp_24h is not None else "")
    )
    return {
        "signal_type": "prediction_market",
        "title": title,
        "content": content,
        "url": f"https://polymarket.com/market/{m.get('slug', '')}" if m.get("slug") else None,
        "occurred_at": datetime.now(timezone.utc),
        "raw_payload": {
            "market_question": question,
            "market_slug": m.get("slug"),
            "yes_probability": yes,
            "no_probability": no,
            "volume_24h": vol,
            "total_volume": total_vol,
            "time_to_resolution_days": days_to_resolution,
            "end_date": end_date,
            "change_pp_24h": change_pp_24h,
        },
    }


def main() -> int:
    session = SessionLocal()
    try:
        source = (
            session.query(Source)
            .filter(
                Source.source_type == SourceType.prediction_market,
                Source.name == "Polymarket",
            )
            .first()
        )
        if not source:
            print(
                "error: Polymarket Source row missing — run scripts/seed_sources.py first",
                file=sys.stderr,
            )
            return 1

        try:
            raw = fetch_markets()
        except Exception as exc:  # noqa: BLE001
            print(f"error: fetch failed: {exc}", file=sys.stderr)
            return 2

        signals: list[dict] = []
        for m in raw:
            sig = to_signal(m)
            if sig:
                signals.append(sig)
            if len(signals) >= TOP_N:
                break

        if not signals:
            print(
                "no crypto-relevant markets found in top batch — nothing to ingest",
                file=sys.stderr,
            )
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUPE_HOURS)
        inserted = 0
        skipped = 0
        for sig in signals:
            slug = sig["raw_payload"]["market_slug"]
            if not slug:
                continue
            recent = (
                session.query(RawSignal.id)
                .filter(
                    RawSignal.source_id == source.id,
                    RawSignal.signal_type == "prediction_market",
                    RawSignal.occurred_at > cutoff,
                    RawSignal.raw_payload["market_slug"].astext == slug,
                )
                .order_by(desc(RawSignal.occurred_at))
                .first()
            )
            if recent:
                skipped += 1
                continue
            session.add(
                RawSignal(
                    source_id=source.id,
                    signal_type=sig["signal_type"],
                    title=sig["title"],
                    content=sig["content"],
                    url=sig["url"],
                    raw_payload=sig["raw_payload"],
                    occurred_at=sig["occurred_at"],
                )
            )
            inserted += 1
        session.commit()

        print(f"considered: {len(signals)} crypto-relevant markets")
        print(f"inserted:   {inserted} (new snapshot or window expired)")
        print(f"skipped:    {skipped} (snapshot within last {DEDUPE_HOURS}h)")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
