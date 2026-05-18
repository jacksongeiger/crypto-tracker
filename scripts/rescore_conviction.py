#!/usr/bin/env python3
"""Re-score conviction on existing brief_themes using the v7 source-count rule.

The synthesis sanitizer used to enforce only the "5 requires multi-type"
ceiling. Themes whose conviction was inflated by signal count (rather than
distinct source count) snuck through. This script applies the new ceiling
from max_conviction_for_counts to every existing theme and UPDATEs anything
that would be downgraded under the current rule.

Read-mostly by default: prints what would change. Pass --apply to write.
Pass --brief <uuid> to limit to a single brief.

Run on the server (where the production DB lives):

    cd ~/crypto-tracker
    backend/.venv/bin/python scripts/rescore_conviction.py            # dry-run
    backend/.venv/bin/python scripts/rescore_conviction.py --apply    # write
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SYNTH_PATH = REPO_ROOT / "skills" / "synthesize-brief" / "scripts" / "synthesize.py"

sys.path.insert(0, str(BACKEND_DIR))
from db import SessionLocal  # noqa: E402
from models import Brief, BriefTheme, RawSignal, Source  # noqa: E402

_spec = importlib.util.spec_from_file_location("synth_for_rescore", SYNTH_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
max_conviction_for_counts = _mod.max_conviction_for_counts


def _theme_counts(session, theme: BriefTheme) -> tuple[int, int]:
    """Return (distinct_source_count, distinct_source_type_count) for the
    theme's cited signals. Looks up each signal_id's Source.id and
    Source.source_type from raw_signals."""
    sig_ids = theme.source_signal_ids or []
    if not sig_ids:
        return 0, 0
    rows = (
        session.query(RawSignal.source_id, Source.source_type)
        .join(Source, Source.id == RawSignal.source_id)
        .filter(RawSignal.id.in_(sig_ids))
        .all()
    )
    sources = {str(r[0]) for r in rows}
    types = {r[1].value if hasattr(r[1], "value") else str(r[1]) for r in rows}
    return len(sources), len(types)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually UPDATE the DB")
    ap.add_argument("--brief", help="restrict to a single brief id")
    args = ap.parse_args()

    session = SessionLocal()
    try:
        q = session.query(BriefTheme).join(Brief, Brief.id == BriefTheme.brief_id)
        if args.brief:
            q = q.filter(Brief.id == args.brief)
        themes = q.order_by(Brief.brief_date.desc(), BriefTheme.display_order.asc()).all()

        downgraded: list[tuple[BriefTheme, int, int, int, int]] = []
        for t in themes:
            if t.conviction_score is None:
                continue
            sc, tc = _theme_counts(session, t)
            ceiling = max_conviction_for_counts(sc, tc)
            if t.conviction_score > ceiling:
                downgraded.append((t, t.conviction_score, ceiling, sc, tc))

        print(f"Scanned {len(themes)} themes; {len(downgraded)} would be downgraded.")
        for t, old, new, sc, tc in downgraded:
            title = (t.title or "")[:70]
            print(
                f"  brief={t.brief_id}  theme={t.id}  "
                f"{old}→{new}  sources={sc} types={tc}  "
                f"title={title!r}"
            )

        if args.apply and downgraded:
            for t, old, new, sc, tc in downgraded:
                t.conviction_score = new
            session.commit()
            print(f"Applied {len(downgraded)} downgrade(s).")
        elif args.apply:
            print("No changes to apply.")
        else:
            print("Dry-run — pass --apply to write.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
