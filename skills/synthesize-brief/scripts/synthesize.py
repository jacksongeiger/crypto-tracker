"""Generate a daily crypto brief from the last 24h of news_signals.

Pipeline:
  1. Query raw_signals (signal_type='news_article') from the last 24h.
  2. Refuse with a clear message if <5 signals (not enough to synthesize).
  3. Load backend/prompts/synthesis_v1.md as system instruction.
  4. Call Gemini 2.5 Flash with structured-JSON output enforced.
  5. Validate response: themes have non-empty source_signal_ids, all IDs
     reference real input signals (hallucination guard), conviction 1-5.
  6. Write briefs + brief_themes in a single transaction.
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
PROMPT_PATH = BACKEND_DIR / "prompts" / "synthesis_v5.md"

VALID_CATEGORIES = frozenset({"policy", "markets", "tech", "adoption", "misc"})
sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal  # noqa: E402
from models import Brief, BriefTheme, RawSignal, Source  # noqa: E402

MIN_SIGNALS = 5
MODEL_NAME = os.environ.get("SYNTH_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.environ.get("SYNTH_TEMPERATURE", "0.4"))
CONTENT_TRUNCATE_CHARS = 1200


def load_signals(session) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = (
        session.query(RawSignal, Source.name)
        .join(Source, Source.id == RawSignal.source_id)
        .filter(
            RawSignal.signal_type == "news_article",
            RawSignal.ingested_at >= cutoff,
        )
        .order_by(RawSignal.occurred_at.desc())
        .all()
    )
    return [
        {
            "signal_id": str(rs.id),
            "source": source_name,
            "occurred_at": rs.occurred_at.isoformat(),
            "title": rs.title,
            "content": (rs.content or "")[:CONTENT_TRUNCATE_CHARS],
        }
        for rs, source_name in rows
    ]


def render_user_message(signals: list[dict], brief_date: str) -> str:
    blocks = []
    for s in signals:
        blocks.append(
            textwrap.dedent(
                f"""\
                - signal_id: {s['signal_id']}
                  source: {s['source']}
                  occurred_at: {s['occurred_at']}
                  title: {s['title']}
                  content: {s['content']}
                """
            )
        )
    return (
        f"Brief date: {brief_date}\n"
        f"Window: last 24 hours\n"
        f"Signal count: {len(signals)}\n\n"
        f"Signals:\n\n" + "\n".join(blocks)
    )


def validate_response(payload: dict, valid_signal_ids: set[str]) -> None:
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
            raise ValueError(
                f"theme[{i}].categories contains unknown values: {bad}"
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
                f"refusing to synthesize: only {len(signals)} news_article "
                f"signals in last 24h (need >= {MIN_SIGNALS})",
                file=sys.stderr,
            )
            return 2

        valid_ids = {s["signal_id"] for s in signals}
        brief_date = datetime.now(timezone.utc).date().isoformat()
        system_prompt = PROMPT_PATH.read_text()
        user_message = render_user_message(signals, brief_date)

        try:
            payload, meta = call_gemini(system_prompt, user_message)
            validate_response(payload, valid_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"synthesis failed: {exc}", file=sys.stderr)
            return 3

        brief = persist(session, payload, signals, meta)
        brief_id = str(brief.id)
        brief_date = brief.brief_date.isoformat()
    finally:
        session.close()

    print(f"brief_id: {brief_id}")
    print(f"brief_date: {brief_date}")
    print(f"input_signals: {len(signals)}")
    print(f"themes: {len(payload['themes'])}")
    print(f"tokens: {meta.get('total_tokens')}")
    print()
    print("=" * 70)
    print(f"SUMMARY:\n{payload['summary']}")
    print("=" * 70)
    for i, t in enumerate(payload["themes"], 1):
        primary_short = t["primary_signal_id"][:8]
        n_corroborators = len(t["source_signal_ids"]) - 1
        print(f"\n[{i}] {t['title']}  (conviction {t['conviction_score']}, "
              f"primary={primary_short}…, +{n_corroborators} corroborators)")
        print(textwrap.fill(t["body"], width=78, initial_indent="    ",
                            subsequent_indent="    "))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
