"""Schema test: confirm brief_themes has the source_types column post-migration."""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")


@pytest.fixture(scope="module")
def engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return create_engine(url)


def test_source_types_column_exists(engine):
    insp = inspect(engine)
    cols = {c["name"]: c for c in insp.get_columns("brief_themes")}
    assert "source_types" in cols, (
        "brief_themes.source_types column missing — has the migration been applied?"
    )
    col = cols["source_types"]
    assert col["nullable"] is True, "source_types should be nullable for backfill flexibility"


def test_source_types_holds_jsonb():
    """The model declaration uses JSONB; check the SQLAlchemy column type."""
    from models import BriefTheme

    col = BriefTheme.__table__.c.source_types
    # Postgres dialect-specific type, named JSONB
    assert col.type.__class__.__name__ == "JSONB"
