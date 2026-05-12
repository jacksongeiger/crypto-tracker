"""Ingest macro indicators from FRED into raw_signals.

Each indicator becomes a signal of a dedicated subtype. We only insert
when the latest data point from FRED is newer than our most recent
existing signal of that subtype — so re-runs are idempotent and the
table builds a time series.

If FRED_API_KEY is unset the skill exits 0 with a clear message rather
than failing — FRED requires a free API key, registered at
https://fredaccount.stlouisfed.org/apikey.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

from sqlalchemy import desc  # noqa: E402

from db import SessionLocal  # noqa: E402
from models import RawSignal, Source, SourceType  # noqa: E402

# Each entry: (subtype, fred_series_id, label, context_blurb)
INDICATORS = [
    (
        "dxy",
        "DTWEXBGS",
        "Trade-Weighted USD",
        "Broad trade-weighted USD index. A stronger dollar usually pressures BTC and risk assets.",
    ),
    (
        "treasury_10y",
        "DGS10",
        "10Y Treasury yield",
        "10-year US Treasury yield. The benchmark long-rate; rising yields raise the discount on duration assets.",
    ),
    (
        "treasury_2y",
        "DGS2",
        "2Y Treasury yield",
        "2-year US Treasury yield. The most rate-policy-sensitive part of the curve.",
    ),
    (
        "fed_funds",
        "DFF",
        "Effective Fed Funds rate",
        "Daily effective federal funds rate. Direct read on Fed policy stance.",
    ),
    (
        "cpi_yoy",
        "CPIAUCSL",
        "CPI YoY",
        "Headline CPI year-over-year (computed from the level series). Hotter CPI means later/slower cuts.",
    ),
    (
        "m2_supply",
        "M2SL",
        "M2 money supply",
        "M2 money supply level. A blunt liquidity proxy that crypto tends to follow with a lag.",
    ),
    (
        "unemployment",
        "UNRATE",
        "Unemployment rate",
        "U-3 unemployment rate. Softening labor data tends to pull rate cuts forward.",
    ),
    (
        "gold_price",
        "GOLDAMGBD228NLBM",
        "Gold (LBMA AM)",
        "London AM gold fix. Gold and BTC are sometimes correlated as alt-stores-of-value.",
    ),
    (
        "sp500",
        "SP500",
        "S&P 500",
        "S&P 500 index level. BTC's beta to the S&P has been positive in recent regimes.",
    ),
    (
        "vix",
        "VIXCLS",
        "VIX",
        "CBOE Volatility Index close. Risk-off macro often shows up here first.",
    ),
]

BASE = "https://api.stlouisfed.org/fred/series/observations"
TIMEOUT = 20


def fetch_observations(series_id: str, api_key: str, limit: int = 14) -> list[dict]:
    """Latest `limit` observations, newest first. Used so we can compute
    a % change off the prior valid reading and (for CPI) YoY off ~12
    months of monthly data."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    r = requests.get(
        BASE, params=params, timeout=TIMEOUT, headers={"User-Agent": "crypto-tracker/0.1"}
    )
    r.raise_for_status()
    return r.json().get("observations", [])


def latest_existing_date(session, source_id, subtype: str) -> Optional[date]:
    row = (
        session.query(RawSignal.occurred_at)
        .filter(
            RawSignal.source_id == source_id,
            RawSignal.signal_type == subtype,
        )
        .order_by(desc(RawSignal.occurred_at))
        .first()
    )
    return row[0].date() if row else None


def _f(v: str) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_signal(subtype: str, label: str, blurb: str, observations: list[dict]) -> Optional[dict]:
    """Build the most-recent signal dict, or None if data isn't usable.

    Computes pct-change-from-prior-reading. For cpi_yoy specifically, we
    compute YoY % off the level 12 readings back.
    """
    valid = [o for o in observations if _f(o.get("value")) is not None]
    if not valid:
        return None
    latest = valid[0]
    latest_val = _f(latest["value"])
    latest_date = date.fromisoformat(latest["date"])

    if subtype == "cpi_yoy":
        # YoY = (latest / 12-readings-back - 1) * 100, monthly series
        if len(valid) < 13:
            return None
        prior = _f(valid[12]["value"])
        if prior is None or prior == 0:
            return None
        yoy = (latest_val / prior - 1) * 100
        title = f"CPI YoY: {yoy:.2f}% ({latest_date.isoformat()})"
        payload = {
            "indicator": label,
            "fred_series_id": "CPIAUCSL",
            "latest_level": latest_val,
            "prior_level_12mo": prior,
            "yoy_pct": yoy,
            "observation_date": latest_date.isoformat(),
        }
        content = (
            f"CPI year-over-year inflation is {yoy:.2f}% as of {latest_date.isoformat()}. "
            + blurb
        )
        return {
            "signal_type": subtype,
            "title": title,
            "content": content,
            "occurred_at": datetime(
                latest_date.year, latest_date.month, latest_date.day, tzinfo=timezone.utc
            ),
            "raw_payload": payload,
        }

    # Generic: pct change from prior valid reading
    prior_val = _f(valid[1]["value"]) if len(valid) > 1 else None
    pct = (
        (latest_val - prior_val) / prior_val * 100
        if prior_val and prior_val != 0
        else None
    )
    pct_str = f"{pct:+.2f}%" if pct is not None else "n/a"
    prior_str = f"{prior_val:,.4g}" if prior_val is not None else "n/a"
    title = f"{label}: {latest_val:,.4g} ({pct_str}) {latest_date.isoformat()}"
    content = (
        f"{label} closed at {latest_val:,.4g} on {latest_date.isoformat()} "
        f"(prior reading {prior_str}, change {pct_str}). "
        + blurb
    )
    payload = {
        "indicator": label,
        "fred_series_id": next(s for sub, s, _, _ in INDICATORS if sub == subtype),
        "latest_value": latest_val,
        "prior_value": prior_val,
        "pct_change_from_prior": pct,
        "observation_date": latest_date.isoformat(),
    }
    return {
        "signal_type": subtype,
        "title": title,
        "content": content,
        "occurred_at": datetime(
            latest_date.year, latest_date.month, latest_date.day, tzinfo=timezone.utc
        ),
        "raw_payload": payload,
    }


def main() -> int:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print(
            "skip: FRED_API_KEY is not set in backend/.env — register a free key at "
            "https://fredaccount.stlouisfed.org/apikey and add it to .env to enable "
            "macro ingestion. Skill noop'd cleanly.",
            file=sys.stderr,
        )
        return 0

    session = SessionLocal()
    try:
        source = (
            session.query(Source)
            .filter(
                Source.source_type == SourceType.macro,
                Source.name == "FRED",
            )
            .first()
        )
        if not source:
            print(
                "error: FRED Source row missing — run scripts/seed_sources.py first",
                file=sys.stderr,
            )
            return 1

        rows: list[tuple[str, str]] = []
        for subtype, series_id, label, blurb in INDICATORS:
            try:
                obs = fetch_observations(series_id, api_key)
                signal = build_signal(subtype, label, blurb, obs)
            except Exception as exc:  # noqa: BLE001
                rows.append((subtype, f"ERROR: {exc}"))
                continue
            if not signal:
                rows.append((subtype, "skipped: no usable observation"))
                continue
            existing = latest_existing_date(session, source.id, subtype)
            if existing and existing >= signal["occurred_at"].date():
                rows.append(
                    (subtype, f"skipped: latest {signal['occurred_at'].date()} not newer than existing {existing}")
                )
                continue
            session.add(
                RawSignal(
                    source_id=source.id,
                    signal_type=signal["signal_type"],
                    title=signal["title"],
                    content=signal["content"],
                    url=f"https://fred.stlouisfed.org/series/{series_id}",
                    raw_payload=signal["raw_payload"],
                    occurred_at=signal["occurred_at"],
                )
            )
            rows.append((subtype, f"inserted ({signal['occurred_at'].date()})"))
        session.commit()

        print(f"{'subtype':<14} {'result'}")
        print("-" * 60)
        for sub, res in rows:
            print(f"{sub:<14} {res}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
