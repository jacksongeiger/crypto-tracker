"""Unit tests for on-chain skill parsing functions.

Tests are pure: no DB, no HTTP. Just exercise the parse_* helpers
against mocked API payloads.
"""
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INGEST_PATH = REPO_ROOT / "skills" / "onchain" / "scripts" / "ingest.py"
_spec = importlib.util.spec_from_file_location("onchain_ingest", INGEST_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["onchain_ingest"] = _mod
_spec.loader.exec_module(_mod)
parse_chains = _mod.parse_chains
parse_dexes = _mod.parse_dexes
parse_fees = _mod.parse_fees
parse_stablecoins = _mod.parse_stablecoins


def test_parse_chains_filters_to_majors_and_emits_pct_string():
    rows = [
        {"name": "Ethereum", "tvl": 45_230_000_000, "change_1d": 1.5, "change_7d": -2.3},
        {"name": "Solana", "tvl": 6_190_000_000, "change_1d": 12.4, "change_7d": 8.1},
        {"name": "Obscure-Chain", "tvl": 1, "change_1d": 0.0, "change_7d": 0.0},
    ]
    out = parse_chains(rows)
    names = [s["raw_payload"]["chain_name"] for s in out]
    assert "Ethereum" in names
    assert "Solana" in names
    assert "Obscure-Chain" not in names
    eth = next(s for s in out if s["raw_payload"]["chain_name"] == "Ethereum")
    assert eth["signal_type"] == "tvl_change"
    assert "+1.50%" in eth["title"]
    assert "$45.23B" in eth["title"]


def test_parse_chains_handles_missing_change():
    rows = [{"name": "Ethereum", "tvl": 1_000_000, "change_1d": None, "change_7d": None}]
    out = parse_chains(rows)
    assert "n/a" in out[0]["title"]


def test_parse_fees_takes_top_20_sorted():
    rows = [
        {"name": f"P{i}", "category": "Lending", "total24h": i * 1000, "change_1d": 1}
        for i in range(1, 31)
    ]
    out = parse_fees(rows)
    assert len(out) == 20
    # Top entry should be the highest total24h
    assert out[0]["raw_payload"]["protocol_name"] == "P30"
    assert out[0]["raw_payload"]["fees_24h_usd"] == 30_000


def test_parse_dexes_includes_volume_and_change():
    rows = [
        {"name": "Uniswap", "total24h": 2_500_000_000, "change_1d": 5.2},
        {"name": "Curve", "total24h": 800_000_000, "change_1d": -1.0},
    ]
    out = parse_dexes(rows)
    assert out[0]["raw_payload"]["dex_name"] == "Uniswap"
    assert out[0]["raw_payload"]["volume_24h_usd"] == 2_500_000_000
    assert "+5.20%" in out[0]["title"]


def test_parse_stablecoins_filters_majors_and_computes_deltas():
    payload = {
        "peggedAssets": [
            {
                "symbol": "USDC",
                "circulating": {"peggedUSD": 110_000_000_000},
                "circulatingPrevDay": {"peggedUSD": 109_000_000_000},
                "circulatingPrevWeek": {"peggedUSD": 105_000_000_000},
            },
            {
                "symbol": "WEIRDCOIN",
                "circulating": {"peggedUSD": 1_000_000},
                "circulatingPrevDay": {"peggedUSD": 1_000_000},
                "circulatingPrevWeek": {"peggedUSD": 1_000_000},
            },
        ]
    }
    out = parse_stablecoins(payload)
    assert len(out) == 1
    sig = out[0]
    assert sig["raw_payload"]["stablecoin"] == "USDC"
    # 24h: (110 - 109) / 109 * 100 ≈ 0.917%
    assert abs(sig["raw_payload"]["change_24h"] - (1_000_000_000 / 109_000_000_000 * 100)) < 1e-9


def test_parse_stablecoins_handles_missing_history():
    payload = {
        "peggedAssets": [
            {
                "symbol": "USDC",
                "circulating": {"peggedUSD": 110_000_000_000},
            }
        ]
    }
    out = parse_stablecoins(payload)
    assert out[0]["raw_payload"]["change_24h"] is None
