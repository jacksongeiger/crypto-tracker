"""One-off: classify existing brief_themes that have no categories yet.

For each theme where categories is empty, sends (title, body) to Gemini
2.5 Flash with a tiny classification prompt and updates the row in
place. Idempotent: themes with a non-empty categories array are skipped.

Usage: backend/.venv/bin/python scripts/backfill_categories.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

from db import SessionLocal  # noqa: E402
from models import BriefTheme  # noqa: E402

MODEL_NAME = "gemini-2.5-flash"
VALID_CATEGORIES = ["policy", "markets", "tech", "ai", "adoption", "misc"]

CLASSIFY_PROMPT = """You are categorizing a single news theme for a crypto-news app.

Categories (pick 1, or at most 2 if the theme genuinely spans two):

- policy: regulation, enforcement, legislation, central banks, courts, sanctions
- markets: capital flows, fundraises, M&A, ETF, treasury behavior, exchange moves
- tech: protocols, infrastructure, standards, L1/L2, security primitives, tooling
- ai: AI ecosystem itself — model releases, agent frameworks (MCP/OpenClaw), developer tools, AI infrastructure, capability announcements. NOT crypto+AI intersections (those are adoption).
- adoption: real-world use, payments, AI-agent + crypto, partnerships putting crypto in front of users
- misc: high-signal stories that don't fit the five above

Return JSON of the form: {"categories": ["..."]}. No prose, no markdown.
"""


def classify(title: str, body: str) -> list[str]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in backend/.env")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=CLASSIFY_PROMPT,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    )
    response = model.generate_content(
        f"THEME TITLE:\n{title}\n\nTHEME BODY:\n{body}"
    )
    payload = json.loads(response.text)
    cats = payload.get("categories", [])
    if not isinstance(cats, list) or not 1 <= len(cats) <= 2:
        raise ValueError(f"bad categories response: {cats!r}")
    bad = [c for c in cats if c not in VALID_CATEGORIES]
    if bad:
        raise ValueError(f"unknown categories: {bad}")
    return cats


def main() -> int:
    session = SessionLocal()
    try:
        themes = (
            session.query(BriefTheme)
            .filter(BriefTheme.categories == [])
            .order_by(BriefTheme.created_at)
            .all()
        )
        if not themes:
            print("nothing to backfill — all themes already have categories")
            return 0
        print(f"backfilling {len(themes)} theme(s)…")
        for theme in themes:
            try:
                cats = classify(theme.title, theme.body)
                theme.categories = cats
                session.commit()
                print(f"  ✓ {theme.title[:60]:<60}  →  {cats}")
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                print(f"  ✗ {theme.title[:60]:<60}  →  {exc}", file=sys.stderr)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
