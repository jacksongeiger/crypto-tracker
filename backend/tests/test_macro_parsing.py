"""Unit tests for macro skill build_signal()."""
import importlib.util
import sys
from datetime import date, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INGEST_PATH = REPO_ROOT / "skills" / "macro" / "scripts" / "ingest.py"
_spec = importlib.util.spec_from_file_location("macro_ingest", INGEST_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["macro_ingest"] = _mod
_spec.loader.exec_module(_mod)
build_signal = _mod.build_signal


def _ob(d: str, v):
    return {"date": d, "value": str(v) if v is not None else "."}


def test_generic_signal_has_pct_change_and_payload():
    obs = [_ob("2026-05-12", 4.55), _ob("2026-05-09", 4.50)]
    sig = build_signal("treasury_10y", "10Y Treasury yield", "blurb.", obs)
    assert sig is not None
    assert sig["signal_type"] == "treasury_10y"
    assert sig["raw_payload"]["latest_value"] == 4.55
    assert sig["raw_payload"]["prior_value"] == 4.50
    pct = sig["raw_payload"]["pct_change_from_prior"]
    assert pct is not None and abs(pct - ((4.55 - 4.50) / 4.50 * 100)) < 1e-9
    assert sig["occurred_at"].tzinfo == timezone.utc
    assert sig["occurred_at"].date() == date(2026, 5, 12)


def test_dotted_observations_skipped_for_value():
    obs = [
        _ob("2026-05-12", None),
        _ob("2026-05-09", 4.50),
        _ob("2026-05-08", 4.48),
    ]
    sig = build_signal("treasury_10y", "10Y", "b.", obs)
    # Latest valid observation is 4.50, prior is 4.48 -> pct ≈ 0.446%
    assert sig["raw_payload"]["latest_value"] == 4.50
    assert sig["raw_payload"]["prior_value"] == 4.48
    pct = sig["raw_payload"]["pct_change_from_prior"]
    assert pct is not None and abs(pct - ((4.50 - 4.48) / 4.48 * 100)) < 1e-9


def test_no_valid_observations_returns_none():
    obs = [_ob("2026-05-12", None), _ob("2026-05-09", None)]
    assert build_signal("treasury_10y", "10Y", "b.", obs) is None


def test_cpi_yoy_computed_off_12mo_prior():
    obs = [
        _ob("2026-05-01", 320.0),  # index 0 = latest
        _ob("2026-04-01", 319.5),
        _ob("2026-03-01", 319.0),
        _ob("2026-02-01", 318.5),
        _ob("2026-01-01", 318.0),
        _ob("2025-12-01", 317.0),
        _ob("2025-11-01", 316.0),
        _ob("2025-10-01", 314.0),
        _ob("2025-09-01", 312.0),
        _ob("2025-08-01", 311.0),
        _ob("2025-07-01", 310.0),
        _ob("2025-06-01", 309.0),
        _ob("2025-05-01", 308.0),  # index 12 = 12 months back
    ]
    sig = build_signal("cpi_yoy", "CPI YoY", "blurb.", obs)
    assert sig is not None
    assert sig["raw_payload"]["latest_level"] == 320.0
    assert sig["raw_payload"]["prior_level_12mo"] == 308.0
    yoy = sig["raw_payload"]["yoy_pct"]
    assert abs(yoy - ((320.0 / 308.0 - 1) * 100)) < 1e-9
    assert "%" in sig["title"]


def test_cpi_yoy_returns_none_with_short_history():
    obs = [_ob(f"2026-0{i}-01", 100 + i) for i in range(1, 6)]  # 5 obs only
    assert build_signal("cpi_yoy", "CPI YoY", "b.", obs) is None
