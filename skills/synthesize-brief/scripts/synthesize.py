"""Generate a daily crypto brief from the last 24h of multi-type signals.

Pipeline:
  1. Query raw_signals across ALL source types from the last 24h, joining
     each to its Source for source_type + name metadata.
  2. Refuse with a clear message if < MIN_SIGNALS (not enough corpus).
  3. Load the v6 prompt as the system instruction.
  4. Call Gemini 2.5 Flash with structured-JSON output enforced.
  5. Validate response: per-theme primary in source_signal_ids, all IDs
     real (hallucination guard), conviction 1-5, categories 1-2 valid,
     source_types non-empty subset of valid SourceType values.
  6. Write briefs + brief_themes (with source_types) in a single tx.
  7. Print brief_id, theme count, and the brief itself to stdout.

Exit codes:
  0  success
  2  not enough signals to synthesize
  3  Gemini call failed or response invalid
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
PROMPT_PATH = BACKEND_DIR / "prompts" / "synthesis_v6.md"

VALID_CATEGORIES = frozenset({"policy", "markets", "tech", "adoption", "misc"})
VALID_SOURCE_TYPES = frozenset(
    {"news_rss", "on_chain", "prediction_market", "macro", "crypto_price"}
)
sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal  # noqa: E402
from models import Brief, BriefTheme, RawSignal, Source  # noqa: E402

MIN_SIGNALS = 20
MODEL_NAME = os.environ.get("SYNTH_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.environ.get("SYNTH_TEMPERATURE", "0.4"))
NEWS_TRUNCATE_CHARS = 800   # tighter than v5's 1200 because corpus is bigger
OTHER_TRUNCATE_CHARS = 600  # non-news content is structured + already short


def load_signals(session) -> list[dict]:
    """Pull every raw_signal ingested in the last 24h with source metadata."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = (
        session.query(RawSignal, Source.name, Source.source_type)
        .join(Source, Source.id == RawSignal.source_id)
        .filter(RawSignal.ingested_at >= cutoff)
        .order_by(RawSignal.occurred_at.desc())
        .all()
    )
    out: list[dict] = []
    for rs, source_name, source_type in rows:
        truncate = (
            NEWS_TRUNCATE_CHARS
            if rs.signal_type == "news_article"
            else OTHER_TRUNCATE_CHARS
        )
        out.append(
            {
                "signal_id": str(rs.id),
                "source": source_name,
                "source_type": source_type.value,
                "signal_type": rs.signal_type,
                "occurred_at": rs.occurred_at.isoformat(),
                "title": rs.title,
                "content": (rs.content or "")[:truncate],
            }
        )
    return out


def render_user_message(signals: list[dict], brief_date: str) -> str:
    blocks = []
    by_type: dict[str, int] = {}
    for s in signals:
        by_type[s["source_type"]] = by_type.get(s["source_type"], 0) + 1
        blocks.append(
            textwrap.dedent(
                f"""\
                - signal_id: {s['signal_id']}
                  source_type: {s['source_type']}
                  signal_type: {s['signal_type']}
                  source: {s['source']}
                  occurred_at: {s['occurred_at']}
                  title: {s['title']}
                  content: {s['content']}
                """
            )
        )
    type_breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_type.items()))
    return (
        f"Brief date: {brief_date}\n"
        f"Window: last 24 hours\n"
        f"Signal count: {len(signals)} ({type_breakdown})\n\n"
        f"Signals:\n\n" + "\n".join(blocks)
    )


def validate_response(
    payload: dict, valid_signal_ids: set[str], signal_type_map: dict[str, str]
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("response is not a JSON object")
    if not isinstance(payload.get("summary"), str) or not payload["summary"].strip():
        raise ValueError("summary missing or empty")
    themes = payload.get("themes")
    if not isinstance(themes, list) or not themes:
        raise ValueError("themes missing or empty")
    if len(themes) > 5:
        raise ValueError(f"too many themes: {len(themes)} (max 5)")
    for i, t in enumerate(themes):
        if not isinstance(t, dict):
            raise ValueError(f"theme[{i}] is not an object")
        for key in ("title", "body"):
            if not isinstance(t.get(key), str) or not t[key].strip():
                raise ValueError(f"theme[{i}].{key} missing or empty")
        ids = t.get("source_signal_ids")
        if not isinstance(ids, list) or not ids:
            raise ValueError(f"theme[{i}].source_signal_ids must be non-empty list")
        unknown = [x for x in ids if x not in valid_signal_ids]
        if unknown:
            raise ValueError(
                f"theme[{i}].source_signal_ids contains unknown IDs: {unknown[:3]}"
            )
        primary = t.get("primary_signal_id")
        if not isinstance(primary, str) or not primary:
            raise ValueError(f"theme[{i}].primary_signal_id missing or empty")
        if primary not in valid_signal_ids:
            raise ValueError(f"theme[{i}].primary_signal_id is not a valid input id: {primary}")
        if primary not in ids:
            raise ValueError(
                f"theme[{i}].primary_signal_id {primary} must also appear in source_signal_ids"
            )
        score = t.get("conviction_score")
        if not isinstance(score, int) or not 1 <= score <= 5:
            raise ValueError(f"theme[{i}].conviction_score must be int 1-5, got {score!r}")
        cats = t.get("categories")
        if not isinstance(cats, list) or not 1 <= len(cats) <= 2:
            raise ValueError(
                f"theme[{i}].categories must be a list of 1-2 strings, got {cats!r}"
            )
        bad = [c for c in cats if c not in VALID_CATEGORIES]
        if bad:
            raise ValueError(f"theme[{i}].categories contains unknown values: {bad}")

        # New in v6: source_types validation
        stypes = t.get("source_types")
        if not isinstance(stypes, list) or not stypes:
            raise ValueError(
                f"theme[{i}].source_types must be a non-empty list of source_type strings"
            )
        bad_st = [s for s in stypes if s not in VALID_SOURCE_TYPES]
        if bad_st:
            raise ValueError(
                f"theme[{i}].source_types contains unknown values: {bad_st}"
            )
        # source_types must match the actual unique source_types of cited signals
        cited_types = {signal_type_map[sid] for sid in ids}
        declared = set(stypes)
        # Allow declared to be a subset of cited (model may legitimately
        # narrow), but reject declared types not present in cited at all.
        extra = declared - cited_types
        if extra:
            raise ValueError(
                f"theme[{i}].source_types declares {sorted(extra)} but no cited signal has those types"
            )
        # Conviction 5 requires multiple distinct source_types
        if score == 5 and len(declared) < 2:
            raise ValueError(
                f"theme[{i}] conviction 5 requires multiple source_types in source_types; got {sorted(declared)}"
            )


def call_gemini(system_prompt: str, user_message: str) -> tuple[dict, dict]:
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in backend/.env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": TEMPERATURE,
        },
    )
    response = model.generate_content(user_message)
    raw_text = response.text
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print("--- raw Gemini response (parse failed) ---", file=sys.stderr)
        print(raw_text, file=sys.stderr)
        raise RuntimeError(f"failed to parse Gemini JSON: {exc}") from exc

    usage = getattr(response, "usage_metadata", None)
    meta = {
        "model": MODEL_NAME,
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
    }
    return parsed, meta


def persist(session, payload: dict, signals: list[dict], meta: dict) -> Brief:
    brief = Brief(
        brief_date=datetime.now(timezone.utc).date(),
        summary=payload["summary"],
        model_used=MODEL_NAME,
        input_signal_count=len(signals),
        generation_metadata=meta,
    )
    session.add(brief)
    session.flush()  # populate brief.id

    for i, t in enumerate(payload["themes"]):
        session.add(
            BriefTheme(
                brief_id=brief.id,
                title=t["title"],
                body=t["body"],
                conviction_score=t.get("conviction_score"),
                primary_signal_id=t["primary_signal_id"],
                source_signal_ids=t["source_signal_ids"],
                categories=t["categories"],
                source_types=t["source_types"],
                display_order=i,
            )
        )
    session.commit()
    return brief


def main() -> int:
    session = SessionLocal()
    try:
        signals = load_signals(session)
        if len(signals) < MIN_SIGNALS:
            print(
                f"refusing to synthesize: only {len(signals)} signals in last 24h "
                f"(need >= {MIN_SIGNALS}). Run the source skills first.",
                file=sys.stderr,
            )
            return 2

        valid_ids = {s["signal_id"] for s in signals}
        signal_type_map = {s["signal_id"]: s["source_type"] for s in signals}
        brief_date = datetime.now(timezone.utc).date().isoformat()
        system_prompt = PROMPT_PATH.read_text()
        user_message = render_user_message(signals, brief_date)

        try:
            payload, meta = call_gemini(system_prompt, user_message)
            validate_response(payload, valid_ids, signal_type_map)
        except Exception as exc:  # noqa: BLE001
            print(f"synthesis failed: {exc}", file=sys.stderr)
            return 3

        brief = persist(session, payload, signals, meta)
        brief_id = str(brief.id)
        brief_date_str = brief.brief_date.isoformat()
    finally:
        session.close()

    # Compute breakdown for display
    by_type: dict[str, int] = {}
    for s in signals:
        by_type[s["source_type"]] = by_type.get(s["source_type"], 0) + 1
    breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_type.items()))

    print(f"brief_id: {brief_id}")
    print(f"brief_date: {brief_date_str}")
    print(f"input_signals: {len(signals)} ({breakdown})")
    print(f"themes: {len(payload['themes'])}")
    print(f"tokens: {meta.get('total_tokens')}")
    print()
    print("=" * 70)
    print(f"SUMMARY:\n{payload['summary']}")
    print("=" * 70)
    for i, t in enumerate(payload["themes"], 1):
        primary_short = t["primary_signal_id"][:8]
        n_corroborators = len(t["source_signal_ids"]) - 1
        types_str = ", ".join(t["source_types"])
        print(
            f"\n[{i}] {t['title']}  "
            f"(conviction {t['conviction_score']}, "
            f"primary={primary_short}…, "
            f"+{n_corroborators} corroborators, "
            f"types=[{types_str}])"
        )
        print(textwrap.fill(t["body"], width=78, initial_indent="    ",
                            subsequent_indent="    "))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
