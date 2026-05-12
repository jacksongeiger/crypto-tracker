"""Pretty-print a daily crypto brief from the database.

Usage:
  backend/.venv/bin/python scripts/read_brief.py                # most recent
  backend/.venv/bin/python scripts/read_brief.py <brief_id>     # specific

Exit codes:
  0  brief rendered
  1  brief_id supplied but not found, or no briefs in the database
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal  # noqa: E402
from models import Brief, BriefTheme, RawSignal, Source  # noqa: E402

WIDTH = 78


def _truncate(s: str, max_len: int) -> str:
    return s if len(s) <= max_len else s[: max_len - 1].rstrip() + "…"


def render(brief: Brief, rows) -> None:
    bar = "═" * WIDTH
    print(bar)
    print(f"  DAILY CRYPTO BRIEF  ·  {brief.brief_date}".ljust(WIDTH))
    print(
        f"  generated {brief.generated_at:%Y-%m-%d %H:%M %Z}  ·  "
        f"{brief.model_used}  ·  {brief.input_signal_count} input signals"
    )
    print(bar)
    print()
    for line in textwrap.wrap(brief.summary, width=WIDTH):
        print(line)
    print()
    print("─" * WIDTH)

    for theme, primary_source, primary_title, primary_url in rows:
        n_corroborators = max(0, len(theme.source_signal_ids) - 1)
        score = theme.conviction_score
        if score is None:
            stars = "?"
            score_label = "?/5"
        else:
            stars = "★" * score + "☆" * (5 - score)
            score_label = f"{score}/5"
        plural = "s" if n_corroborators != 1 else ""

        print()
        for line in textwrap.wrap(
            f"[{theme.display_order + 1}] {theme.title}", width=WIDTH
        ):
            print(line)
        print(
            f"    conviction {stars} ({score_label})  ·  "
            f"primary: {primary_source}  ·  "
            f"+{n_corroborators} corroborating source{plural}"
        )
        print()
        for line in textwrap.wrap(theme.body, width=WIDTH - 4):
            print(f"    {line}")
        print()
        print(f"    ↳ {_truncate(primary_title, WIDTH - 6)}")
        if primary_url:
            print(f"      {_truncate(primary_url, WIDTH - 6)}")
        print()
        print("─" * WIDTH)


def main() -> int:
    brief_id = sys.argv[1] if len(sys.argv) > 1 else None
    session = SessionLocal()
    try:
        if brief_id:
            brief = session.query(Brief).filter(Brief.id == brief_id).first()
            if not brief:
                print(f"error: no brief with id={brief_id}", file=sys.stderr)
                return 1
        else:
            brief = (
                session.query(Brief).order_by(Brief.generated_at.desc()).first()
            )
            if not brief:
                print(
                    "error: no briefs in the database — run the "
                    "synthesize-brief skill first",
                    file=sys.stderr,
                )
                return 1

        rows = (
            session.query(BriefTheme, Source.name, RawSignal.title, RawSignal.url)
            .join(RawSignal, RawSignal.id == BriefTheme.primary_signal_id)
            .join(Source, Source.id == RawSignal.source_id)
            .filter(BriefTheme.brief_id == brief.id)
            .order_by(BriefTheme.display_order)
            .all()
        )
        render(brief, rows)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
