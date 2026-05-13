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
DEFAULT_PROMPT = BACKEND_DIR / "prompts" / "synthesis_v7.md"
PROMPT_PATH = Path(os.environ.get("SYNTH_PROMPT", str(DEFAULT_PROMPT)))

VALID_CATEGORIES = frozenset({"policy", "markets", "tech", "adoption", "misc", "ai"})
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
    """Pull every raw_signal *occurring* in the last 24h with source metadata.

    Filtering on `occurred_at` (publication date / snapshot timestamp)
    rather than `ingested_at` means a backfill of historical RSS posts
    (e.g. when a new feed source is added that exposes its full archive)
    doesn't contaminate today's brief with months-old content. Snapshot
    signals (on-chain, macro, predictions, sentiment) all use
    occurred_at=now() so they're unaffected.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = (
        session.query(RawSignal, Source.name, Source.source_type)
        .join(Source, Source.id == RawSignal.source_id)
        .filter(RawSignal.occurred_at >= cutoff)
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


SYSTEMIC_DROP_THRESHOLD = 0.5


def sanitize_response(
    payload: dict, valid_signal_ids: set[str], signal_type_map: dict[str, str]
) -> dict:
    """Clean a Gemini response in-place: drop hallucinated signal IDs, drop
    irrecoverable themes, recompute source_types and auto-downgrade conviction
    if cleaning broke the multi-type-for-5 rule. Returns a drop report.

    Raises ValueError only on **systemic** failures:
      - response not a dict / themes empty / summary empty
      - >SYSTEMIC_DROP_THRESHOLD of themes had to be dropped entirely
      - cleaning left zero themes
      - cleaned themes still violate a non-recoverable rule
    """
    report: dict = {"dropped_signals": [], "dropped_themes": [], "auto_corrected": []}

    if not isinstance(payload, dict):
        raise ValueError("response is not a JSON object")
    if not isinstance(payload.get("summary"), str) or not payload["summary"].strip():
        raise ValueError("summary missing or empty")
    themes = payload.get("themes")
    if not isinstance(themes, list) or not themes:
        raise ValueError("themes missing or empty")
    original_count = len(themes)
    if original_count > 5:
        # Truncate excess rather than fail
        report["auto_corrected"].append(
            {"kind": "truncate_themes", "from": original_count, "to": 5}
        )
        themes = themes[:5]

    cleaned: list[dict] = []
    for i, t in enumerate(themes):
        title_for_log = (t.get("title") or "<no title>")[:80] if isinstance(t, dict) else "<not a dict>"

        if not isinstance(t, dict):
            report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": "not an object"})
            continue
        for key in ("title", "body"):
            if not isinstance(t.get(key), str) or not t[key].strip():
                report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": f"{key} missing or empty"})
                break
        else:
            # ── clean source_signal_ids ──
            ids = t.get("source_signal_ids")
            if not isinstance(ids, list):
                report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": "source_signal_ids not a list"})
                continue
            unknown = [x for x in ids if x not in valid_signal_ids]
            known = [x for x in ids if x in valid_signal_ids]
            if unknown:
                report["dropped_signals"].append(
                    {"theme_index": i, "title": title_for_log, "dropped": unknown}
                )
            if not known:
                report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": "no valid source_signal_ids remain"})
                continue
            t["source_signal_ids"] = known

            # ── primary_signal_id must survive cleaning ──
            primary = t.get("primary_signal_id")
            if not isinstance(primary, str) or primary not in valid_signal_ids:
                # Try to recover by promoting the first remaining known signal as primary
                report["auto_corrected"].append(
                    {"kind": "primary_promoted", "theme_index": i,
                     "old": primary, "new": known[0]}
                )
                primary = known[0]
                t["primary_signal_id"] = primary
            if primary not in known:
                # Primary survived valid_ids but isn't in cleaned source list — fold it in
                known.append(primary)
                t["source_signal_ids"] = known

            # ── conviction_score ──
            score = t.get("conviction_score")
            if not isinstance(score, int) or not 1 <= score <= 5:
                report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": f"invalid conviction_score: {score!r}"})
                continue

            # ── categories: drop invalid entries (e.g. model put a source_type
            #    in the categories field) but keep theme if >=1 valid remains ──
            cats = t.get("categories")
            if not isinstance(cats, list) or not cats:
                report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": f"categories missing or not a list: {cats!r}"})
                continue
            valid_cats = [c for c in cats if c in VALID_CATEGORIES][:2]  # cap at 2
            if not valid_cats:
                report["dropped_themes"].append({"index": i, "title": title_for_log, "reason": f"no valid categories in {cats!r}"})
                continue
            if valid_cats != cats:
                report["auto_corrected"].append(
                    {"kind": "categories_cleaned", "theme_index": i,
                     "from": cats, "to": valid_cats}
                )
                t["categories"] = valid_cats

            # ── source_types: rebuild from the cleaned id set so it is honest ──
            cited_types = sorted({signal_type_map[sid] for sid in known if sid in signal_type_map})
            declared = t.get("source_types")
            if not isinstance(declared, list) or not declared:
                t["source_types"] = cited_types
                report["auto_corrected"].append(
                    {"kind": "source_types_rebuilt", "theme_index": i, "new": cited_types}
                )
            else:
                # Drop any declared types not actually cited; keep order stable
                kept = [s for s in declared if s in cited_types and s in VALID_SOURCE_TYPES]
                if set(kept) != set(declared):
                    report["auto_corrected"].append(
                        {"kind": "source_types_pruned", "theme_index": i,
                         "from": declared, "to": kept or cited_types}
                    )
                t["source_types"] = kept or cited_types

            # ── conviction 5 requires multi-type; auto-downgrade if cleaning broke it ──
            if t["conviction_score"] == 5 and len(set(t["source_types"])) < 2:
                report["auto_corrected"].append(
                    {"kind": "conviction_downgraded_5_to_4",
                     "theme_index": i, "title": title_for_log,
                     "reason": "post-cleaning only one source_type remains"}
                )
                t["conviction_score"] = 4

            cleaned.append(t)

    if not cleaned:
        raise ValueError("sanitization left zero themes — response unusable")
    drop_ratio = len(report["dropped_themes"]) / original_count
    if drop_ratio > SYSTEMIC_DROP_THRESHOLD:
        raise ValueError(
            f"systemic failure: dropped {len(report['dropped_themes'])}/{original_count} themes "
            f"(>{int(SYSTEMIC_DROP_THRESHOLD*100)}% threshold)"
        )

    payload["themes"] = cleaned
    return report


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
    dry_run = "--dry-run" in sys.argv
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

        # Attempt synthesis, sanitize hallucinated IDs, retry once on systemic failure.
        sanitize_report: dict = {}
        last_raw_payload: dict | None = None
        for attempt in (1, 2):
            try:
                payload, meta = call_gemini(system_prompt, user_message)
                last_raw_payload = json.loads(json.dumps(payload))  # deep copy for logging
                sanitize_report = sanitize_response(payload, valid_ids, signal_type_map)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 1:
                    print(
                        f"synthesis attempt 1 failed: {exc}; retrying once",
                        file=sys.stderr,
                    )
                    continue
                print(f"synthesis failed after retry: {exc}", file=sys.stderr)
                if last_raw_payload is not None:
                    print(
                        "--- raw Gemini payload from final attempt ---",
                        file=sys.stderr,
                    )
                    print(
                        json.dumps(last_raw_payload, indent=2)[:4000],
                        file=sys.stderr,
                    )
                return 3

        # Log sanitization actions so we can track frequency over time.
        if sanitize_report.get("dropped_signals"):
            print(
                f"sanitization: dropped hallucinated IDs from "
                f"{len(sanitize_report['dropped_signals'])} theme(s)",
                file=sys.stderr,
            )
            for d in sanitize_report["dropped_signals"]:
                print(
                    f"  theme {d['theme_index']} ({d['title']!r}): dropped "
                    f"{len(d['dropped'])} bad id(s): {d['dropped']}",
                    file=sys.stderr,
                )
        if sanitize_report.get("dropped_themes"):
            print(
                f"sanitization: dropped {len(sanitize_report['dropped_themes'])} "
                f"theme(s) entirely",
                file=sys.stderr,
            )
            for d in sanitize_report["dropped_themes"]:
                print(
                    f"  theme {d['index']} ({d['title']!r}): {d['reason']}",
                    file=sys.stderr,
                )
        if sanitize_report.get("auto_corrected"):
            print(
                f"sanitization: applied {len(sanitize_report['auto_corrected'])} "
                f"auto-correction(s)",
                file=sys.stderr,
            )
            for c in sanitize_report["auto_corrected"]:
                print(f"  {c}", file=sys.stderr)
        # Persist the sanitization summary on the brief so it's recoverable.
        if isinstance(meta, dict):
            meta["sanitization"] = {
                "dropped_signal_count": sum(
                    len(d["dropped"]) for d in sanitize_report.get("dropped_signals", [])
                ),
                "dropped_themes": len(sanitize_report.get("dropped_themes", [])),
                "auto_corrected_count": len(
                    sanitize_report.get("auto_corrected", [])
                ),
            }

        if dry_run:
            brief_id = "DRY-RUN (not persisted)"
            brief_date_str = datetime.now(timezone.utc).date().isoformat()
        else:
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
