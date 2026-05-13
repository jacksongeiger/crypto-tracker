"""v7 anti-bucketing validators.

Heuristic checks that catch the failure modes v7 was designed to prevent.
These are syntactic/structural checks; semantic same-event verification
needs an LLM judge which we skip per the spec's "if too expensive" carve-out.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Load synthesize.py under a unique module name (avoids collision with the
# skill ingest scripts that share the bare name "ingest").
SYNTH_PATH = REPO_ROOT / "skills" / "synthesize-brief" / "scripts" / "synthesize.py"
_spec = importlib.util.spec_from_file_location("synth_v7", SYNTH_PATH)
_synth = importlib.util.module_from_spec(_spec)
sys.modules["synth_v7"] = _synth
_spec.loader.exec_module(_synth)


# ── Test helpers ─────────────────────────────────────────────────────────

# Conjunction patterns that signal title-level bucketing. " and " is
# bucketing only when joining different subjects; we look for it adjacent
# to two distinct capitalized noun phrases.
BANNED_TITLE_RE = re.compile(
    r"\b(plus|while|amid|alongside|as well as)\b"
    r"|\s\+\s"
    r"|\s&\s",
    re.IGNORECASE,
)
# Stricter title check used for the "two-subject and" case
AND_BETWEEN_SUBJECTS_RE = re.compile(
    r"\b[A-Z][\w&\-]+(?:\s[A-Z][\w&\-]+)*\s+and\s+[A-Z][\w&\-]+",
)

# A short list of company/protocol names we expect to see in current-corpus
# briefs. Used by the body-multi-entity heuristic.
KNOWN_ENTITIES = {
    "Circle", "DTCC", "Chainlink", "Franklin Templeton", "Kraken",
    "Payward", "Coinbase", "Binance", "Kalshi", "Polymarket",
    "MicroStrategy", "Strategy", "Bhutan", "Ark Invest", "BlackRock",
    "Solana", "Ethereum", "Bitcoin", "Tron", "Securitize", "Computershare",
    "Curve", "Uniswap", "Exodus", "BisonFi", "GoonFi", "Saylor",
    "Senate", "CFTC", "SEC", "Federal Reserve",
}


def title_has_banned_conjunction(title: str) -> bool:
    """True if title contains a banned bucketing conjunction."""
    if BANNED_TITLE_RE.search(title):
        return True
    # "and" between two capitalized subjects (heuristic — false-positives
    # on names like "Standard & Poor's" handled by the bare " and " check
    # below which only fires when both sides start with proper-noun caps).
    return bool(AND_BETWEEN_SUBJECTS_RE.search(title))


def body_extra_entities(title: str, body: str) -> set[str]:
    """Return entities mentioned in the body that don't appear in the title.
    Heuristic for body-level bucketing: a single-event theme should be about
    the entity in the title; surplus other entities suggest mixed events."""
    title_lower = title.lower()
    in_body: set[str] = set()
    for ent in KNOWN_ENTITIES:
        if ent.lower() in body.lower() and ent.lower() not in title_lower:
            in_body.add(ent)
    return in_body


# ── Validators ───────────────────────────────────────────────────────────

def assert_no_and_in_titles(themes: list[dict]) -> None:
    bad = [(t["title"]) for t in themes if title_has_banned_conjunction(t["title"])]
    if bad:
        joined = "\n  ".join(bad)
        raise AssertionError(
            f"Title-level bucketing detected (banned conjunction joining subjects):\n  {joined}"
        )


def assert_single_event_in_body(themes: list[dict], max_extra: int = 1) -> None:
    """Heuristic: each theme's body should not introduce >max_extra
    DIFFERENT KNOWN entities not named in the title."""
    failures = []
    for t in themes:
        extras = body_extra_entities(t["title"], t["body"])
        if len(extras) > max_extra:
            failures.append(f"{t['title']!r}\n    extra entities in body: {sorted(extras)}")
    if failures:
        joined = "\n  ".join(failures)
        raise AssertionError(
            f"Body-level bucketing — themes mention >{max_extra} extra known entities:\n  {joined}"
        )


# ── Unit tests ───────────────────────────────────────────────────────────

class TestNoAndInTitles:
    def test_clean_titles_pass(self):
        themes = [
            {"title": "Kraken settles with SEC for $30M and ends US staking"},
            # ^ "and" but joins two aspects of one event (settle + halt)
            {"title": "DTCC partners Chainlink for collateral system"},
            {"title": "Senate Banking releases CLARITY Act draft"},
        ]
        # The middle "and" doesn't trigger our two-subject regex
        # (no capitalized noun phrase on both sides).
        assert_no_and_in_titles(themes)

    def test_two_subjects_with_plus_fails(self):
        themes = [{"title": "DTCC partners Chainlink + Franklin Templeton with Kraken"}]
        with pytest.raises(AssertionError, match="bucketing"):
            assert_no_and_in_titles(themes)

    def test_two_subjects_with_while_fails(self):
        themes = [{"title": "Senate advances CLARITY Act while CFTC eyes prediction markets"}]
        with pytest.raises(AssertionError, match="bucketing"):
            assert_no_and_in_titles(themes)

    def test_two_subjects_with_ampersand_fails(self):
        themes = [{"title": "DTCC & Franklin Templeton both pursue tokenization"}]
        with pytest.raises(AssertionError, match="bucketing"):
            assert_no_and_in_titles(themes)


class TestSingleEventInBody:
    def test_single_event_body_passes(self):
        themes = [
            {
                "title": "Circle raises $222M for Arc institutional blockchain",
                "body": "Circle closed a $222M presale at $3B FDV with backing from BlackRock and a16z.",
            }
        ]
        # Body mentions BlackRock (1 extra known entity) — within limit
        assert_single_event_in_body(themes)

    def test_circle_arc_plus_ai_agents_fails(self):
        # The exact v6 failure mode: Circle Arc presale + Circle AI agents
        # bundled in one body. Body mentions Ark Invest as additional entity.
        themes = [
            {
                "title": "Circle raises $222M for Arc institutional blockchain",
                "body": (
                    "Circle closed a $222M presale at $3B FDV. Ark Invest "
                    "subsequently bought $5.5M of Circle shares. Circle also "
                    "launched USDC tools enabling AI agents to transact, "
                    "expanding stablecoin utility into Coinbase-adjacent flows."
                ),
            }
        ]
        with pytest.raises(AssertionError, match="bucketing"):
            assert_single_event_in_body(themes, max_extra=1)


class TestV7AgainstKnownBadBrief:
    """Sanity: feeding v6's known-bad failure modes through the v7 validators
    should raise. Confirms the validators actually catch real failures."""

    KNOWN_BAD_THEMES = [
        # The on-chain bucket from v6: Curve + Uniswap + Tron + Ethereum
        {
            "title": "On-Chain Activity Surges with Double-Digit Increases in DEX Volumes and Network Fees",
            "body": (
                "Several decentralized exchanges experienced significant 24-hour volume "
                "increases, with Curve DEX volume more than doubling by 105.94%. Other "
                "DEXs like BisonFi (+45.90%), Uniswap V4 (+35.72%), and GoonFi (+35.42%) "
                "also saw substantial growth. Concurrently, major chains and protocols "
                "reported notable increases in 24-hour fee revenue, including Tron "
                "(+76.92%), Ethereum (+37.47%), Solana (+33.53%)."
            ),
        },
        # The TradFi bucket: DTCC + Franklin Templeton in one theme
        {
            "title": "TradFi Deepens Crypto Integration with DTCC-Chainlink Collateral System and Franklin Templeton-Kraken Tokenization Partnership",
            "body": (
                "DTCC is collaborating with Chainlink to build a blockchain-based "
                "collateral management system. Concurrently, Franklin Templeton and "
                "Kraken's parent company, Payward, have partnered to explore launching "
                "new tokenized versions of financial instruments."
            ),
        },
    ]

    def test_v6_onchain_bucket_caught(self):
        # The on-chain title contains "and" joining two distinct things
        # (DEX Volumes AND Network Fees) — should fail body multi-entity.
        with pytest.raises(AssertionError):
            assert_single_event_in_body([self.KNOWN_BAD_THEMES[0]], max_extra=2)

    def test_v6_tradfi_bucket_caught(self):
        # Title joins DTCC-Chainlink with Franklin-Kraken via "and"
        with pytest.raises(AssertionError, match="bucketing"):
            assert_no_and_in_titles([self.KNOWN_BAD_THEMES[1]])


class TestPrimaryEventDominanceSkipped:
    """Per the spec: skip if a stub LLM judge is needed and would be too
    expensive. We rely on the same-event prompt rule + body multi-entity
    heuristic above for the v7 production guarantee."""

    @pytest.mark.skip(reason="needs LLM judge — see test_single_event_in_body for the syntactic backstop")
    def test_primary_event_dominance(self):
        pass
