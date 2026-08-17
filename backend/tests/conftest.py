"""
pytest configuration and shared fixtures for the Law Firm ERP backend tests.

Strategy:
  - Uses a SQLite in-memory database so tests run without PostgreSQL.
  - Overrides the FastAPI app's `get_db` dependency to use the in-memory DB.
  - Each test gets a clean database (tables created fresh, dropped after).
  - The email ingestion service's file-storage path is overridden to use
    a temporary directory so tests don't write to data/emails/ingested/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure `app` is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# In-memory SQLite engine (no PostgreSQL required for tests)
# ---------------------------------------------------------------------------
SQLITE_URL = "sqlite://"  # pure in-memory, discarded after test

TEST_ENGINE = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
)


def _get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """Create all tables, yield a session, drop everything after the test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def client(db_session, tmp_path, monkeypatch):
    """
    FastAPI TestClient with:
      - get_db overridden to use the in-memory SQLite DB
      - email ingestion storage directory redirected to tmp_path
    """
    # Override the DB dependency
    app.dependency_overrides[get_db] = lambda: (yield db_session)

    # Redirect file storage so tests don't write to data/
    import app.services.email_ingestion as svc
    monkeypatch.setattr(svc, "INGESTED_EMAIL_DIR", tmp_path / "ingested")

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# .eml file helpers
# ---------------------------------------------------------------------------
_EML_DIR = Path(__file__).parent.parent.parent / "data" / "emails" / "matter_1"

def eml_bytes(email_id: str) -> bytes:
    """Return raw bytes of a Matter 1 test .eml file."""
    return (_EML_DIR / f"{email_id}.eml").read_bytes()
