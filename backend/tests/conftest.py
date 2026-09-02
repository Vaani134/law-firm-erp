"""
pytest configuration and shared fixtures for the Law Firm ERP backend tests.

Strategy:
  - Uses the real PostgreSQL database (same one the app uses).
  - SQLite cannot be used because the schema uses PostgreSQL-specific types
    (JSONB, UUID) that SQLite does not support.
  - Each test COMMITS its own data during the test, then the fixture
    deletes it in teardown using the known PKs.
  - The email ingestion service's file-storage path is overridden to a
    temporary directory so tests never write to data/emails/ingested/.
  - A session-scoped autouse fixture seeds Matter 1 (10001-001) and its
    participants before any test runs. The seed is idempotent and is
    imported from scripts/seed_matter_1.py — production behavior is
    unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app

# ---------------------------------------------------------------------------
# PostgreSQL engine for tests
# ---------------------------------------------------------------------------
TEST_ENGINE = create_engine(settings.database_url, pool_pre_ping=True)

TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Session-scoped seed fixture: ensure Matter 1 (10001-001) exists.
# ---------------------------------------------------------------------------
# Several tests in this suite reference the production seed matter
# 10001-001 ("Harbor Spirits / Riverside Liquors Acquisition") and its
# 4 participants. Without this fixture those tests fail with
# ForeignKeyViolation because the matter row is not present in the DB.
#
# The seeding logic itself lives in scripts/seed_matter_1.py and is
# idempotent (it no-ops if Matter 10001-001 already exists). We import
# and call it in-process so the test suite is self-contained.
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture(scope="session", autouse=True)
def _ensure_matter_1_seed():
    """Seed Matter 10001-001 and its participants if not already present."""
    import seed_matter_1  # noqa: WPS433 — intentional in-process import
    seed_matter_1.run_seed()
    yield


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """
    Yield a fresh session for each test.
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session, tmp_path, monkeypatch):
    """
    FastAPI TestClient backed by a real PostgreSQL session.
    Clean up test data after each test.
    """
    from app.models.email import Email
    from app.models.matter import Matter
    from app.models.matter_participant import MatterParticipant
    from app.models.case_brain_log import CaseBrainLog

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override

    import app.services.email_ingestion as svc
    monkeypatch.setattr(svc, "INGESTED_EMAIL_DIR", tmp_path / "ingested")

    try:
        with TestClient(app) as c:
            yield c
    finally:
        # Clean up all test data (except production seed data)
        # Delete in reverse order of foreign key dependencies
        db_session.query(CaseBrainLog).delete()
        db_session.query(Email).delete()
        db_session.query(MatterParticipant).filter(MatterParticipant.matter_key.like('TEST-%')).delete()
        db_session.query(Matter).filter(Matter.matter_key.like('TEST-%')).delete()
        # Also clean up any test matters created with other patterns
        db_session.query(Matter).filter(Matter.client_id == 'TEST').delete()
        db_session.commit()

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# .eml file helpers
# ---------------------------------------------------------------------------
_EML_DIR = Path(__file__).parent.parent.parent / "data" / "emails" / "matter_1"

def eml_bytes(email_id: str) -> bytes:
    return (_EML_DIR / f"{email_id}.eml").read_bytes()
