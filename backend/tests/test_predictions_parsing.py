"""Unit tests for predictions skill parse helpers."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skills" / "predictions" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from ingest import looks_crypto, parse_yes_prob, to_signal  # noqa: E402


def test_looks_crypto_matches_keyword_substrings():
    assert looks_crypto("Will Bitcoin hit $150k by Dec 31?")
    assert looks_crypto("SEC vs Coinbase settlement before EOY?")
    assert looks_crypto("Fed Funds rate cut in November?")
    assert not looks_crypto("Will the Lakers win the championship?")
    assert not looks_crypto("")


def test_parse_yes_prob_clamps_and_handles_garbage():
    assert parse_yes_prob('["0.62","0.38"]') == 0.62
    assert parse_yes_prob('["0.0","1.0"]') == 0.0
    assert parse_yes_prob("not-json") is None
    assert parse_yes_prob(None) is None
    # Out-of-range silently rejected
    assert parse_yes_prob('["1.5","-0.5"]') is None


def test_to_signal_filters_non_crypto():
    m = {
        "question": "Lakers win NBA?",
        "volume24hr": "10000",
        "outcomePrices": '["0.5","0.5"]',
    }
    assert to_signal(m) is None


def test_to_signal_filters_low_volume():
    m = {
        "question": "Bitcoin hits $200k by 2030?",
        "volume24hr": "5",  # below MIN_24H_VOLUME
        "outcomePrices": '["0.05","0.95"]',
    }
    assert to_signal(m) is None


def test_to_signal_emits_full_payload_for_crypto_market():
    m = {
        "question": "Will BTC hit $150k by June 30, 2026?",
        "slug": "btc-150k",
        "volume24hr": "12500",
        "volume": "85000",
        "outcomePrices": '["0.04","0.96"]',
        "endDate": "2026-06-30T00:00:00Z",
        "oneDayPriceChange": -0.02,  # 2pp drop
    }
    sig = to_signal(m)
    assert sig is not None
    assert sig["signal_type"] == "prediction_market"
    assert sig["url"] == "https://polymarket.com/market/btc-150k"
    p = sig["raw_payload"]
    assert p["market_slug"] == "btc-150k"
    assert p["yes_probability"] == 0.04
    assert p["no_probability"] == 0.96
    assert p["volume_24h"] == 12500
    assert p["total_volume"] == 85000
    assert p["change_pp_24h"] == -2.0
    assert "4.0% YES" in sig["title"]
    assert "(-2.0pp 24h)" in sig["title"]


def test_to_signal_handles_missing_change():
    m = {
        "question": "Will SEC approve a Solana ETF in 2026?",
        "slug": "sol-etf",
        "volume24hr": "9000",
        "outcomePrices": '["0.30","0.70"]',
    }
    sig = to_signal(m)
    assert sig is not None
    assert sig["raw_payload"]["change_pp_24h"] is None
    # Title omits the (..pp 24h) suffix when change is missing
    assert "pp 24h" not in sig["title"]
