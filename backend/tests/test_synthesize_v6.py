"""Tests for synthesize.py v6 multi-type input + validation."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skills" / "synthesize-brief" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from synthesize import (  # noqa: E402
    VALID_CATEGORIES,
    VALID_SOURCE_TYPES,
    render_user_message,
    validate_response,
)


# ── render_user_message: confirm prompt input carries source_type tags ──

def test_render_includes_source_type_and_signal_type_for_each_signal():
    signals = [
        {
            "signal_id": "n1",
            "source": "CoinDesk",
            "source_type": "news_rss",
            "signal_type": "news_article",
            "occurred_at": "2026-05-12T10:00:00+00:00",
            "title": "Foo Corp news",
            "content": "Body text",
        },
        {
            "signal_id": "o1",
            "source": "Defillama",
            "source_type": "on_chain",
            "signal_type": "tvl_change",
            "occurred_at": "2026-05-12T10:00:00+00:00",
            "title": "Solana TVL +12%",
            "content": "Solana TVL is up.",
        },
    ]
    msg = render_user_message(signals, "2026-05-12")
    assert "Brief date: 2026-05-12" in msg
    # type breakdown shows both
    assert "news_rss=1" in msg
    assert "on_chain=1" in msg
    # each signal block carries its tags
    assert "source_type: news_rss" in msg
    assert "signal_type: news_article" in msg
    assert "source_type: on_chain" in msg
    assert "signal_type: tvl_change" in msg


# ── validator: source_types is required and must be valid ──

VALID_IDS = {"n1", "o1", "p1", "m1"}
TYPE_MAP = {
    "n1": "news_rss",
    "o1": "on_chain",
    "p1": "prediction_market",
    "m1": "macro",
}


def _theme(**overrides):
    base = {
        "title": "Foo Corp partners with Bar for X",
        "body": "Foo Corp announced a thing.",
        "primary_signal_id": "n1",
        "source_signal_ids": ["n1"],
        "categories": ["markets"],
        "source_types": ["news_rss"],
        "conviction_score": 2,
    }
    base.update(overrides)
    return base


def _payload(themes):
    return {"summary": "Summary text.", "themes": themes}


def test_valid_v6_payload_passes():
    validate_response(_payload([_theme()]), VALID_IDS, TYPE_MAP)


def test_source_types_required():
    with pytest.raises(ValueError, match="source_types must be a non-empty list"):
        validate_response(
            _payload([_theme(source_types=None)]), VALID_IDS, TYPE_MAP
        )


def test_source_types_unknown_value_rejected():
    with pytest.raises(ValueError, match="source_types contains unknown values"):
        validate_response(
            _payload([_theme(source_types=["bogus_type"])]), VALID_IDS, TYPE_MAP
        )


def test_source_types_must_match_cited_signals():
    # Theme cites only n1 (news_rss) but declares on_chain -> reject
    with pytest.raises(ValueError, match="no cited signal has those types"):
        validate_response(
            _payload(
                [
                    _theme(
                        source_signal_ids=["n1"],
                        source_types=["on_chain"],
                    )
                ]
            ),
            VALID_IDS,
            TYPE_MAP,
        )


def test_conviction_5_requires_multiple_source_types():
    # Single-type theme can't score 5
    with pytest.raises(
        ValueError, match="conviction 5 requires multiple source_types"
    ):
        validate_response(
            _payload([_theme(conviction_score=5)]),
            VALID_IDS,
            TYPE_MAP,
        )


def test_conviction_5_with_multiple_source_types_passes():
    # Cite two types and declare both
    theme = _theme(
        primary_signal_id="n1",
        source_signal_ids=["n1", "o1"],
        source_types=["news_rss", "on_chain"],
        conviction_score=5,
    )
    validate_response(_payload([theme]), VALID_IDS, TYPE_MAP)


def test_all_valid_source_types_individually_accepted():
    for st, sid in [
        ("news_rss", "n1"),
        ("on_chain", "o1"),
        ("prediction_market", "p1"),
        ("macro", "m1"),
    ]:
        validate_response(
            _payload(
                [
                    _theme(
                        primary_signal_id=sid,
                        source_signal_ids=[sid],
                        source_types=[st],
                    )
                ]
            ),
            VALID_IDS,
            TYPE_MAP,
        )


def test_constants_exposed():
    assert "news_rss" in VALID_SOURCE_TYPES
    assert "policy" in VALID_CATEGORIES
