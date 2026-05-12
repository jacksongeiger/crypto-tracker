"""Unit tests for sentiment skill parsing."""
import sys
from datetime import timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skills" / "sentiment" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from ingest import parse  # noqa: E402


def _payload(*rows):
    return {"data": list(rows)}


def test_parse_emits_value_and_classification():
    out = parse(
        _payload(
            {"value": "49", "value_classification": "Neutral", "timestamp": "1747008000"}
        )
    )
    assert out["signal_type"] == "fear_greed"
    assert out["raw_payload"]["value"] == 49
    assert out["raw_payload"]["classification"] == "Neutral"
    assert "Fear & Greed: 49 (Neutral)" in out["title"]


def test_parse_includes_yesterday_when_present():
    out = parse(
        _payload(
            {"value": "70", "value_classification": "Greed", "timestamp": "1747008000"},
            {"value": "55", "value_classification": "Neutral", "timestamp": "1746921600"},
        )
    )
    assert out["raw_payload"]["value_yesterday"] == 55
    assert out["raw_payload"]["classification_yesterday"] == "Neutral"
    # Title nods to the change because classifications differ
    assert "was Neutral yesterday" in out["title"]


def test_parse_no_change_message_when_classification_same():
    out = parse(
        _payload(
            {"value": "55", "value_classification": "Neutral", "timestamp": "1747008000"},
            {"value": "52", "value_classification": "Neutral", "timestamp": "1746921600"},
        )
    )
    assert "was" not in out["title"]


def test_parse_handles_only_today():
    out = parse(
        _payload(
            {"value": "30", "value_classification": "Fear", "timestamp": "1747008000"}
        )
    )
    assert out["raw_payload"]["value_yesterday"] is None


def test_parse_raises_on_empty_data():
    with pytest.raises(ValueError):
        parse({"data": []})


def test_parse_occurred_at_is_utc():
    out = parse(
        _payload(
            {"value": "49", "value_classification": "Neutral", "timestamp": "1747008000"}
        )
    )
    assert out["occurred_at"].tzinfo == timezone.utc
