"""Tests for sanitize_response — the graceful recovery layer added on top of
validate_response so v7 synthesis tolerates hallucinated signal IDs and
similar non-systemic model errors."""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTH_PATH = REPO_ROOT / "skills" / "synthesize-brief" / "scripts" / "synthesize.py"
_spec = importlib.util.spec_from_file_location("synth_for_sanitize", SYNTH_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["synth_for_sanitize"] = _mod
_spec.loader.exec_module(_mod)

sanitize_response = _mod.sanitize_response


VALID_IDS = {f"sig-{i}" for i in range(10)}
TYPE_MAP = {f"sig-{i}": "news_rss" for i in range(10)}
# Diversify a few to test source_types rebuilding
TYPE_MAP["sig-1"] = "on_chain"
TYPE_MAP["sig-2"] = "prediction_market"
TYPE_MAP["sig-3"] = "macro"

# Default each signal to its own distinct source so existing tests
# remain "cross-source" by default. Specific tests override this to
# simulate same-source-many-signals scenarios.
SOURCE_MAP = {f"sig-{i}": f"src-{i}" for i in range(10)}


def _theme(**overrides):
    base = {
        "title": "Foo Corp announces something concrete",
        "body": "Specific factual claim about Foo Corp.",
        "primary_signal_id": "sig-0",
        "source_signal_ids": ["sig-0"],
        "categories": ["markets"],
        "source_types": ["news_rss"],
        "conviction_score": 2,
    }
    base.update(overrides)
    return base


def _payload(themes):
    return {"summary": "summary text", "themes": themes}


# ── Happy path: clean response passes unchanged ──

def test_clean_response_no_corrections():
    payload = _payload([_theme()])
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert report["dropped_signals"] == []
    assert report["dropped_themes"] == []
    assert report["auto_corrected"] == []


# ── Hallucinated IDs ──

def test_drops_one_hallucinated_id_from_a_theme():
    payload = _payload(
        [
            _theme(
                source_signal_ids=["sig-0", "not-a-real-id"],
            )
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert len(report["dropped_signals"]) == 1
    assert report["dropped_signals"][0]["dropped"] == ["not-a-real-id"]
    assert payload["themes"][0]["source_signal_ids"] == ["sig-0"]
    assert report["dropped_themes"] == []


def test_drops_theme_when_all_ids_hallucinated():
    payload = _payload(
        [
            _theme(
                primary_signal_id="bogus-1",
                source_signal_ids=["bogus-1", "bogus-2"],
            ),
            _theme(),  # this one survives
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert len(report["dropped_themes"]) == 1
    assert "no valid source_signal_ids remain" in report["dropped_themes"][0]["reason"]
    assert len(payload["themes"]) == 1


def test_promotes_new_primary_when_old_primary_is_hallucinated_but_corroborator_is_real():
    payload = _payload(
        [
            _theme(
                primary_signal_id="bogus-primary",
                source_signal_ids=["bogus-primary", "sig-0"],
            )
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    # Bogus dropped from source_signal_ids, primary promoted to sig-0
    assert payload["themes"][0]["source_signal_ids"] == ["sig-0"]
    assert payload["themes"][0]["primary_signal_id"] == "sig-0"
    promoted = [c for c in report["auto_corrected"] if c["kind"] == "primary_promoted"]
    assert promoted, "expected a primary_promoted auto-correction entry"


# ── source_types is rebuilt to be honest ──

def test_source_types_rebuilt_from_cleaned_ids():
    payload = _payload(
        [
            _theme(
                primary_signal_id="sig-0",
                source_signal_ids=["sig-0", "sig-1", "bogus-id"],  # bogus dropped
                source_types=["news_rss", "on_chain", "macro"],   # macro is now a lie
            )
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    # macro had no cited signal (sig-0=news, sig-1=on_chain after cleaning)
    assert "macro" not in payload["themes"][0]["source_types"]
    pruned = [c for c in report["auto_corrected"] if c["kind"] == "source_types_pruned"]
    assert pruned


def test_source_types_rebuilt_when_missing():
    payload = _payload(
        [
            _theme(
                primary_signal_id="sig-0",
                source_signal_ids=["sig-0", "sig-1"],
                source_types=[],  # missing/empty
            )
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    # Should be rebuilt from cited signal source_types
    assert set(payload["themes"][0]["source_types"]) == {"news_rss", "on_chain"}
    assert any(c["kind"] == "source_types_rebuilt" for c in report["auto_corrected"])


# ── Conviction auto-downgrade when cleaning broke multi-type ──

def test_conviction_5_downgraded_when_cleaning_leaves_single_type():
    # Cited both news + on_chain originally with score 5; one of them is bogus
    payload = _payload(
        [
            _theme(
                primary_signal_id="sig-0",  # news_rss
                source_signal_ids=["sig-0", "bogus-onchain"],  # bogus dropped
                source_types=["news_rss", "on_chain"],
                conviction_score=5,
            )
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    # After cleaning only sig-0 remains: 1 source, 1 type → ceiling 2
    assert payload["themes"][0]["conviction_score"] == 2
    downgrade = [
        c
        for c in report["auto_corrected"]
        if c["kind"] == "conviction_downgraded_by_source_count"
    ]
    assert downgrade and downgrade[0]["from"] == 5


def test_conviction_5_preserved_when_multi_type_survives_cleaning():
    payload = _payload(
        [
            _theme(
                primary_signal_id="sig-0",  # news_rss
                source_signal_ids=["sig-0", "sig-1", "bogus"],  # bogus dropped, news+on_chain remain
                source_types=["news_rss", "on_chain"],
                conviction_score=5,
            )
        ]
    )
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert payload["themes"][0]["conviction_score"] == 5
    assert len(payload["themes"][0]["source_types"]) >= 2


# ── Systemic failures ──

def test_systemic_raise_when_majority_themes_dropped():
    # 4 themes, 3 with all-hallucinated ids → 75% dropped > 50% threshold
    bad = lambda: _theme(  # noqa: E731
        primary_signal_id="bogus-x",
        source_signal_ids=["bogus-x"],
    )
    payload = _payload([bad(), bad(), bad(), _theme()])
    with pytest.raises(ValueError, match="systemic failure"):
        sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)


def test_systemic_raise_when_summary_missing():
    payload = {"summary": "", "themes": [_theme()]}
    with pytest.raises(ValueError, match="summary missing or empty"):
        sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)


def test_systemic_raise_when_all_themes_dropped():
    payload = _payload(
        [
            _theme(primary_signal_id="bogus", source_signal_ids=["bogus"]),
        ]
    )
    with pytest.raises(ValueError, match="zero themes"):
        sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)


# ── Categories: clean don't drop ──

def test_categories_cleaned_when_mixed_with_invalid_value():
    # Model accidentally put a source_type ('macro') in categories alongside
    # a valid category ('policy'). Should keep the theme with just 'policy'.
    payload = _payload([_theme(categories=["macro", "policy"])])
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert payload["themes"][0]["categories"] == ["policy"]
    cleaned = [c for c in report["auto_corrected"] if c["kind"] == "categories_cleaned"]
    assert cleaned and cleaned[0]["from"] == ["macro", "policy"]
    assert cleaned[0]["to"] == ["policy"]
    assert report["dropped_themes"] == []


def test_categories_dropped_only_when_zero_valid():
    payload = _payload([_theme(categories=["macro", "bogus"])])
    with pytest.raises(ValueError, match="zero themes"):
        sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)


def test_categories_capped_at_two():
    payload = _payload([_theme(categories=["policy", "markets", "tech"])])
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert payload["themes"][0]["categories"] == ["policy", "markets"]


# ── Too-many-themes is auto-corrected, not raised ──

def test_too_many_themes_truncated_to_5():
    payload = _payload([_theme(primary_signal_id=f"sig-{i}", source_signal_ids=[f"sig-{i}"]) for i in range(7)])
    report = sanitize_response(payload, VALID_IDS, TYPE_MAP, SOURCE_MAP)
    assert len(payload["themes"]) == 5
    truncs = [c for c in report["auto_corrected"] if c["kind"] == "truncate_themes"]
    assert truncs and truncs[0]["from"] == 7 and truncs[0]["to"] == 5


# ── Conviction ceiling by distinct sources (not signal count) ──

def _same_source_setup(n: int):
    """Build a (valid_ids, type_map, source_map) trio where every signal
    comes from the SAME source (one Defillama, many on-chain snapshots)."""
    valid = {f"defi-{i}" for i in range(n)}
    type_map = {f"defi-{i}": "on_chain" for i in range(n)}
    source_map = {f"defi-{i}": "src-defillama" for i in range(n)}
    return valid, type_map, source_map


def test_many_same_source_signals_capped_at_conviction_2():
    """8 Defillama signals from one source = 1 effective source,
    1 source_type → max conviction 2 even if model declared 5."""
    valid, type_map, source_map = _same_source_setup(8)
    payload = _payload(
        [
            _theme(
                primary_signal_id="defi-0",
                source_signal_ids=[f"defi-{i}" for i in range(8)],
                source_types=["on_chain"],
                conviction_score=5,  # inflated — only 1 unique source
            )
        ]
    )
    report = sanitize_response(payload, valid, type_map, source_map)
    assert payload["themes"][0]["conviction_score"] == 2
    downgrade = [
        c
        for c in report["auto_corrected"]
        if c["kind"] == "conviction_downgraded_by_source_count"
    ]
    assert downgrade, "expected source-count-based downgrade"
    assert downgrade[0]["source_count"] == 1
    assert downgrade[0]["type_count"] == 1
    assert downgrade[0]["from"] == 5
    assert downgrade[0]["to"] == 2


def test_cross_type_imbalanced_still_earns_5():
    """8 Defillama signals + 1 Fear & Greed = 2 sources across 2 source_types
    → conviction 5 is still valid because cross-type."""
    valid = {f"defi-{i}" for i in range(8)} | {"fg-0"}
    type_map = {f"defi-{i}": "on_chain" for i in range(8)}
    type_map["fg-0"] = "macro"
    source_map = {f"defi-{i}": "src-defillama" for i in range(8)}
    source_map["fg-0"] = "src-fear-greed"

    payload = _payload(
        [
            _theme(
                primary_signal_id="defi-0",
                source_signal_ids=[f"defi-{i}" for i in range(8)] + ["fg-0"],
                source_types=["on_chain", "macro"],
                conviction_score=5,
            )
        ]
    )
    report = sanitize_response(payload, valid, type_map, source_map)
    # 2 source_types → ceiling is 5; no downgrade
    assert payload["themes"][0]["conviction_score"] == 5
    assert not [
        c
        for c in report["auto_corrected"]
        if c["kind"] == "conviction_downgraded_by_source_count"
    ]


def test_two_same_type_sources_capped_at_3():
    """2 distinct news_rss outlets, same type → max conviction 3."""
    valid = {"news-a", "news-b"}
    type_map = {"news-a": "news_rss", "news-b": "news_rss"}
    source_map = {"news-a": "src-coindesk", "news-b": "src-theblock"}
    payload = _payload(
        [
            _theme(
                primary_signal_id="news-a",
                source_signal_ids=["news-a", "news-b"],
                source_types=["news_rss"],
                conviction_score=4,  # declared too high
            )
        ]
    )
    report = sanitize_response(payload, valid, type_map, source_map)
    assert payload["themes"][0]["conviction_score"] == 3
    downgrade = [
        c
        for c in report["auto_corrected"]
        if c["kind"] == "conviction_downgraded_by_source_count"
    ]
    assert downgrade and downgrade[0]["to"] == 3


def test_three_same_type_sources_allow_4():
    """3 distinct news_rss outlets, same type → conviction 4 stands."""
    valid = {"news-a", "news-b", "news-c"}
    type_map = {sid: "news_rss" for sid in valid}
    source_map = {"news-a": "src-coindesk", "news-b": "src-theblock", "news-c": "src-decrypt"}
    payload = _payload(
        [
            _theme(
                primary_signal_id="news-a",
                source_signal_ids=["news-a", "news-b", "news-c"],
                source_types=["news_rss"],
                conviction_score=4,
            )
        ]
    )
    report = sanitize_response(payload, valid, type_map, source_map)
    assert payload["themes"][0]["conviction_score"] == 4
    assert not [
        c
        for c in report["auto_corrected"]
        if c["kind"] == "conviction_downgraded_by_source_count"
    ]


def test_single_source_conviction_2_unchanged():
    """1 source single-type theme declared as 2 stays at 2 (model judges concrete vs speculative)."""
    valid = {"news-a"}
    type_map = {"news-a": "news_rss"}
    source_map = {"news-a": "src-theblock"}
    payload = _payload(
        [
            _theme(
                primary_signal_id="news-a",
                source_signal_ids=["news-a"],
                source_types=["news_rss"],
                conviction_score=2,
            )
        ]
    )
    report = sanitize_response(payload, valid, type_map, source_map)
    assert payload["themes"][0]["conviction_score"] == 2
    assert not [
        c
        for c in report["auto_corrected"]
        if c["kind"] == "conviction_downgraded_by_source_count"
    ]


# ── max_conviction_for_counts unit table ──

def test_max_conviction_for_counts_table():
    f = _mod.max_conviction_for_counts
    # (source_count, type_count) → expected ceiling
    cases = [
        (1, 1, 2),
        (2, 1, 3),
        (3, 1, 4),
        (5, 1, 4),
        (1, 2, 5),  # cross-type even with 1 source per type
        (2, 2, 5),
        (3, 3, 5),
        (0, 0, 2),  # degenerate
    ]
    for sc, tc, expected in cases:
        assert f(sc, tc) == expected, f"counts=({sc},{tc}) → expected {expected}"
