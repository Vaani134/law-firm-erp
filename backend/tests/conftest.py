"""
pytest configuration and shared fixtures for the Law Firm ERP backend tests.

Strategy:
  - Uses an ISOLATED PostgreSQL database (law_firm_erp_test).
  - The development FastAPI server uses law_firm_erp.
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

SAFETY:
  The test engine is configured to use ONLY law_firm_erp_test.
  If the configured database is anything else, pytest will fail at
  collection time rather than risk running tests against production
  or development data.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Test database isolation
# ---------------------------------------------------------------------------
# The application reads DATABASE_URL from .env / environment. For tests we
# MUST NOT use that directly — pytest must use a separate database so that
# destructive teardown (Email/CaseBrainLog deletes) cannot touch
# development data.

_TEST_DB_NAME = "law_firm_erp_test"


def _build_test_database_url(dev_url: str) -> str:
    """Replace the database name in a SQLAlchemy URL with the test database name."""
    url = make_url(dev_url)
    if not url.database:
        raise ValueError(f"Cannot parse DATABASE_URL for test isolation: {dev_url}")
    return url.set(database=_TEST_DB_NAME).render_as_string(hide_password=False)


_TEST_DATABASE_URL = _build_test_database_url(settings.database_url)

# Safety guard: fail loudly if the test URL does not point to law_firm_erp_test.
# This prevents accidental configuration mistakes from ever pointing pytest
# at the development database.
if f"/{_TEST_DB_NAME}" not in _TEST_DATABASE_URL:
    raise RuntimeError(
        f"Refusing to run tests: test database URL does not contain "
        f"expected database name '{_TEST_DB_NAME}'. "
        f"Configured test URL: {_TEST_DATABASE_URL}"
    )

# ---------------------------------------------------------------------------
# PostgreSQL engine for tests — ISOLATED from development
# ---------------------------------------------------------------------------
TEST_ENGINE = create_engine(_TEST_DATABASE_URL, pool_pre_ping=True)

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
    """Seed Matter 10001-001 and its participants in the TEST database if not already present."""
    from app.models.matter import Matter
    from app.models.matter_participant import MatterParticipant

    db = TestingSessionLocal()
    try:
        existing = db.get(Matter, "10001-001")
        _ensure_minimal_eml_participant(db)
        if existing is not None:
            print("Matter 10001-001 already exists in test database.")
            yield
            return

        matter = Matter(
            matter_key="10001-001",
            client_id="10001",
            matter_id="001",
            client_name="Harbor Spirits Holdings LLC",
            matter_name="Harbor Spirits / Riverside Liquors Acquisition",
            practice_area="Corporate",
            matter_type="M&A - Asset Purchase",
            matter_description=(
                "Representation of Harbor Spirits Holdings LLC in the purchase of "
                "substantially all assets of Riverside Liquors, an operating retail "
                "liquor store in Montclair, New Jersey. The store operates from leased "
                "premises. Transaction is structured as an asset purchase. Discussed "
                "purchase price approximately $1.15 million. Scope includes furniture, "
                "fixtures, equipment, trade name, goodwill and certain inventory. "
                "Premises lease assignment and liquor-license transfer must be addressed."
            ),
            matter_aliases_identifiers=(
                "Harbor Spirits; Riverside Liquors; Riverside Liquors LLC; "
                "10001-001; Harbor Spirits Acquisition; Liquor Store Asset Purchase; "
                "Montclair NJ liquor store"
            ),
            matter_status="open",
            primary_attorney="Sarah Patel",
        )
        db.add(matter)
        db.flush()

        participants = [
            MatterParticipant(
                matter_key="10001-001",
                participant_name="Maya Desai",
                email_address="maya.desai@harborspirits.example",
                organization="Harbor Spirits Holdings LLC",
                role_relationship="client",
                is_active=True,
            ),
            MatterParticipant(
                matter_key="10001-001",
                participant_name="Kevin Russo",
                email_address="kevin.russo@riversideliquors.example",
                organization="Riverside Liquors LLC",
                role_relationship="seller",
                is_active=True,
            ),
            MatterParticipant(
                matter_key="10001-001",
                participant_name="Anthony Bell",
                email_address="abell@bellmercer.example",
                organization="Bell & Mercer LLP",
                role_relationship="opposing_counsel",
                is_active=True,
            ),
            MatterParticipant(
                matter_key="10001-001",
                participant_name="Sarah Patel",
                email_address="spatel@samplelaw.example",
                organization="Sample Law Firm",
                role_relationship="primary_attorney",
                is_active=True,
            ),
        ]
        for p in participants:
            db.add(p)

        db.commit()
        print(f"Matter 10001-001 seeded in test database with {len(participants)} participants.")
    finally:
        db.close()

    yield


def _ensure_minimal_eml_participant(db) -> None:
    """Ensure the MINIMAL_EML sender/recipient can resolve to a Matter.

    Adds alice@example.com and bob@example.com as participants of Matter
    10001-001 so they survive test teardown (which only deletes TEST-%
    matters/participants).
    """
    from app.models.matter_participant import MatterParticipant

    # Check if already present to avoid duplicates across repeated test runs.
    existing = (
        db.query(MatterParticipant)
        .filter(MatterParticipant.matter_key == "10001-001")
        .filter(MatterParticipant.email_address == "alice@example.com")
        .first()
    )
    if existing is not None:
        return

    db.add(
        MatterParticipant(
            matter_key="10001-001",
            participant_name="Alice",
            email_address="alice@example.com",
            organization="Test Org",
            role_relationship="client",
            is_active=True,
        )
    )
    db.add(
        MatterParticipant(
            matter_key="10001-001",
            participant_name="Bob",
            email_address="bob@example.com",
            organization="Test Org",
            role_relationship="client",
            is_active=True,
        )
    )
    db.commit()
    print("MINIMAL_EML participants added to Matter 10001-001 in test database.")


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
