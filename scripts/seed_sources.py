"""Seed the sources table with starter crypto-news RSS feeds.

Idempotent: skips rows whose (source_type, url) already exist.
Run from repo root:  python scripts/seed_sources.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from db import SessionLocal  # noqa: E402
from models import Source, SourceType  # noqa: E402

STARTER_SOURCES = [
    # News (RSS)
    {
        "name": "CoinDesk",
        "source_type": SourceType.news_rss,
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    },
    {
        "name": "The Block",
        "source_type": SourceType.news_rss,
        "url": "https://www.theblock.co/rss.xml",
    },
    {
        "name": "Decrypt",
        "source_type": SourceType.news_rss,
        "url": "https://decrypt.co/feed",
    },
    {
        "name": "Bankless",
        "source_type": SourceType.news_rss,
        "url": "https://www.bankless.com/feed",
    },
    # On-chain
    {
        "name": "Defillama",
        "source_type": SourceType.on_chain,
        "url": "https://defillama.com",
    },
    # Macro / sentiment
    {
        "name": "Fear & Greed Index",
        "source_type": SourceType.macro,
        "url": "https://alternative.me/crypto/fear-and-greed-index/",
    },
    {
        "name": "FRED",
        "source_type": SourceType.macro,
        "url": "https://fred.stlouisfed.org/",
    },
    # Prediction markets
    {
        "name": "Polymarket",
        "source_type": SourceType.prediction_market,
        "url": "https://polymarket.com",
    },
]


def main() -> int:
    session = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for row in STARTER_SOURCES:
            exists = (
                session.query(Source)
                .filter(
                    Source.source_type == row["source_type"],
                    Source.url == row["url"],
                )
                .first()
            )
            if exists:
                skipped += 1
                print(f"  skip   {row['name']:<10}  (already present)")
                continue
            session.add(Source(**row))
            inserted += 1
            print(f"  insert {row['name']:<10}  {row['url']}")
        session.commit()
        print(f"\nDone. inserted={inserted}, skipped={skipped}")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
