"""Unit tests for synthesize.py's validate_response.

Does not hit Gemini or the DB; just exercises the pure validation function.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skills" / "synthesize-brief" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from synthesize import VALID_CATEGORIES, validate_response  # noqa: E402


VALID_IDS = {f"sig-{i}" for i in range(10)}
# All sig-N map to news_rss for these tests — older v5-shaped cases that
# still exercise category/primary/source-id rules. v6-specific multi-type
# behavior is covered in test_synthesize_v6.py.
TYPE_MAP = {sid: "news_rss" for sid in VALID_IDS}


def _theme(**overrides):
    base = {
        "title": "A specific event occurred at Foo Corp",
        "body": "Foo Corp announced a thing. The Block reports details.",
        "primary_signal_id": "sig-0",
        "source_signal_ids": ["sig-0", "sig-1"],
        "categories": ["markets"],
        "source_types": ["news_rss"],
        "conviction_score": 3,
    }
    base.update(overrides)
    return base


def _payload(themes):
    return {"summary": "Today's summary.", "themes": themes}


def test_valid_payload_passes():
    validate_response(_payload([_theme()]), VALID_IDS, TYPE_MAP)


def test_categories_required():
    with pytest.raises(ValueError, match="categories must be a list"):
        validate_response(
            _payload([_theme(categories=None)]),
            VALID_IDS,
            TYPE_MAP,
        )


def test_categories_empty_rejected():
    with pytest.raises(ValueError, match="categories must be a list"):
        validate_response(
            _payload([_theme(categories=[])]),
            VALID_IDS,
            TYPE_MAP,
        )


def test_categories_too_many_rejected():
    with pytest.raises(ValueError, match="categories must be a list"):
        validate_response(
            _payload(
                [_theme(categories=["policy", "markets", "tech"])]
            ),
            VALID_IDS,
            TYPE_MAP,
        )


def test_categories_unknown_value_rejected():
    with pytest.raises(ValueError, match="unknown values"):
        validate_response(
            _payload([_theme(categories=["bogus"])]),
            VALID_IDS,
            TYPE_MAP,
        )


def test_each_valid_category_individually_accepted():
    for cat in VALID_CATEGORIES:
        validate_response(
            _payload([_theme(categories=[cat])]),
            VALID_IDS,
            TYPE_MAP,
        )


def test_primary_must_be_in_source_signal_ids():
    with pytest.raises(ValueError, match="must also appear in source_signal_ids"):
        validate_response(
            _payload(
                [
                    _theme(
                        primary_signal_id="sig-0",
                        source_signal_ids=["sig-1", "sig-2"],
                    )
                ]
            ),
            VALID_IDS,
            TYPE_MAP,
        )


def test_hallucinated_source_signal_id_rejected():
    with pytest.raises(ValueError, match="unknown IDs"):
        validate_response(
            _payload(
                [
                    _theme(
                        primary_signal_id="sig-0",
                        source_signal_ids=["sig-0", "not-a-real-id"],
                    )
                ]
            ),
            VALID_IDS,
            TYPE_MAP,
        )
