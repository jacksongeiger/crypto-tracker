"""Ingest on-chain snapshots from DefiLlama into raw_signals.

Sub-types:
  - tvl_change      Per-chain TVL with 24h/7d % change (top 8 majors)
  - fee_revenue     Top protocols by 24h fees (top 20)
  - dex_volume      Top DEXes by 24h volume (top 10)
  - stablecoin_supply  USDC/USDT/DAI/FDUSD supply with deltas

These are snapshots, not events. occurred_at = now(). url is omitted
because Defillama page URLs are not stable per-snapshot. raw_payload
captures the structured data for later querying.
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

from db import SessionLocal  # noqa: E402
from models import RawSignal, Source, SourceType  # noqa: E402

CHAINS = [
    "Ethereum",
    "Solana",
    "Tron",
    "BSC",
    "Bitcoin",
    "Base",
    "Arbitrum",
    "Polygon",
]
STABLES = {"USDC", "USDT", "DAI", "FDUSD"}
TIMEOUT = 20


def _http_get_json(url: str) -> Any:
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "crypto-tracker/0.1"})
    r.raise_for_status()
    return r.json()


def parse_chains(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    by_name = {r.get("name"): r for r in rows if r.get("name")}
    for chain in CHAINS:
        r = by_name.get(chain)
        if not r:
            continue
        tvl = r.get("tvl") or 0
        d1 = r.get("change_1d")
        d7 = r.get("change_7d")
        d1_str = f"{d1:+.2f}%" if isinstance(d1, (int, float)) else "n/a"
        title = f"{chain} TVL {d1_str} to ${tvl/1e9:,.2f}B over 24h"
        content = (
            f"{chain} total value locked is ${tvl:,.0f}. "
            f"24h change: {d1_str}. "
            f"7d change: {f'{d7:+.2f}%' if isinstance(d7, (int, float)) else 'n/a'}."
        )
        out.append(
            {
                "signal_type": "tvl_change",
                "title": title,
                "content": content,
                "raw_payload": {
                    "chain_name": chain,
                    "current_tvl_usd": tvl,
                    "change_24h_pct": d1,
                    "change_7d_pct": d7,
                },
            }
        )
    return out


def parse_fees(rows: list[dict]) -> list[dict]:
    rows = sorted(
        [r for r in rows if r.get("total24h")],
        key=lambda r: r.get("total24h", 0),
        reverse=True,
    )[:20]
    out: list[dict] = []
    for r in rows:
        name = r.get("name", "?")
        category = r.get("category", "?")
        fees = r.get("total24h") or 0
        change = r.get("change_1d")
        change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "n/a"
        title = f"{name} 24h fees: ${fees:,.0f} ({change_str})"
        content = f"{name} ({category}) collected ${fees:,.0f} in fees over the last 24h. 24h change: {change_str}."
        out.append(
            {
                "signal_type": "fee_revenue",
                "title": title,
                "content": content,
                "raw_payload": {
                    "protocol_name": name,
                    "category": category,
                    "fees_24h_usd": fees,
                    "fees_24h_pct_change": change,
                },
            }
        )
    return out


def parse_dexes(rows: list[dict]) -> list[dict]:
    rows = sorted(
        [r for r in rows if r.get("total24h")],
        key=lambda r: r.get("total24h", 0),
        reverse=True,
    )[:10]
    out: list[dict] = []
    for r in rows:
        name = r.get("name", "?")
        vol = r.get("total24h") or 0
        change = r.get("change_1d")
        change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else "n/a"
        title = f"{name} 24h DEX volume: ${vol/1e9:,.2f}B ({change_str})"
        content = (
            f"{name} processed ${vol:,.0f} in 24h spot DEX volume. 24h change: {change_str}."
        )
        out.append(
            {
                "signal_type": "dex_volume",
                "title": title,
                "content": content,
                "raw_payload": {
                    "dex_name": name,
                    "volume_24h_usd": vol,
                    "change_24h_pct": change,
                },
            }
        )
    return out


def parse_stablecoins(payload: dict) -> list[dict]:
    """`/stablecoins?includePrices=true` returns {peggedAssets: [...]}."""
    assets = payload.get("peggedAssets") or []
    out: list[dict] = []
    for a in assets:
        sym = (a.get("symbol") or "").upper()
        if sym not in STABLES:
            continue
        circ = a.get("circulating") or {}
        supply = circ.get("peggedUSD") or 0
        prev_day = (a.get("circulatingPrevDay") or {}).get("peggedUSD")
        prev_week = (a.get("circulatingPrevWeek") or {}).get("peggedUSD")
        d1 = (
            (supply - prev_day) / prev_day * 100
            if prev_day
            else None
        )
        d7 = (
            (supply - prev_week) / prev_week * 100
            if prev_week
            else None
        )
        d1_str = f"{d1:+.2f}%" if d1 is not None else "n/a"
        d7_str = f"{d7:+.2f}%" if d7 is not None else "n/a"
        title = f"{sym} supply: ${supply/1e9:,.2f}B (24h {d1_str}, 7d {d7_str})"
        content = (
            f"{sym} total circulating supply is ${supply:,.0f}. "
            f"24h change: {d1_str}. 7d change: {d7_str}."
        )
        out.append(
            {
                "signal_type": "stablecoin_supply",
                "title": title,
                "content": content,
                "raw_payload": {
                    "stablecoin": sym,
                    "total_supply": supply,
                    "change_24h": d1,
                    "change_7d": d7,
                },
            }
        )
    return out


def gather_signals() -> list[dict]:
    """Hit all four Defillama endpoints, parse, return combined signal list."""
    chains = _http_get_json("https://api.llama.fi/v2/chains")
    fees = _http_get_json(
        "https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
    ).get("protocols", [])
    dexes = _http_get_json(
        "https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
    ).get("protocols", [])
    stables = _http_get_json("https://stablecoins.llama.fi/stablecoins?includePrices=true")

    return [
        *parse_chains(chains),
        *parse_fees(fees),
        *parse_dexes(dexes),
        *parse_stablecoins(stables),
    ]


def main() -> int:
    session = SessionLocal()
    try:
        source = (
            session.query(Source)
            .filter(
                Source.source_type == SourceType.on_chain,
                Source.name == "Defillama",
            )
            .first()
        )
        if not source:
            print(
                "error: Defillama Source row missing — run scripts/seed_sources.py first",
                file=sys.stderr,
            )
            return 1
        try:
            signals = gather_signals()
        except Exception as exc:  # noqa: BLE001
            print(f"error: failed to gather Defillama signals: {exc}", file=sys.stderr)
            return 2

        now = datetime.now(timezone.utc)
        inserted = 0
        for s in signals:
            session.add(
                RawSignal(
                    source_id=source.id,
                    signal_type=s["signal_type"],
                    title=s["title"],
                    content=s["content"],
                    url=None,
                    raw_payload=s["raw_payload"],
                    occurred_at=now,
                )
            )
            inserted += 1
        session.commit()

        # Per-subtype summary
        by_type: dict[str, int] = {}
        for s in signals:
            by_type[s["signal_type"]] = by_type.get(s["signal_type"], 0) + 1
        print(f"{'subtype':<22} {'inserted':>8}")
        print("-" * 32)
        for k in sorted(by_type):
            print(f"{k:<22} {by_type[k]:>8}")
        print("-" * 32)
        print(f"total inserted: {inserted}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
