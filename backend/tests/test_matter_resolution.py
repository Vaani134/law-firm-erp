"""
Tests for the Matter Resolution service and endpoint.

Coverage:
  1. Exact participant email match → status=resolved, matter_key set,
     processing_status=MATTER_IDENTIFIED
  2. No match → status=unresolved, matter_key=NULL, processing_status unchanged
  3. Already-resolved email → status=already_resolved, no DB change
  4. Sender match resolves correctly (not just To/CC)
  5. CC address match resolves correctly
  6. Ambiguous match (addresses span two Matters) → unresolved
  7. Unknown email_id → 404
  8. matter_key written to DB after successful resolution
  9. processing_status written to MATTER_IDENTIFIED after successful resolution
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import status

# ---------------------------------------------------------------------------
# Seed helpers — use unique matter_keys per test to avoid PK collisions
# ---------------------------------------------------------------------------

def _mk() -> str:
    """Generate a unique test matter key that won't collide with real data."""
    return f"TEST-{uuid.uuid4().hex[:8]}"


def _seed_matter(db, client=None, matter_key: str | None = None):
    from app.models.matter import Matter
    if matter_key is None:
        matter_key = _mk()
    
    # Check if matter already exists
    existing = db.query(Matter).filter(Matter.matter_key == matter_key).first()
    if existing:
        return existing
    
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for resolution tests",
        matter_status="open",
    )
    db.add(m)
    # Don't commit - let the test framework handle it
    db.flush()  # Generate ID without committing
    return m


def _seed_participant(db, matter_key, email_address, name="Test Participant"):
    from app.models.matter_participant import MatterParticipant
    p = MatterParticipant(
        matter_key=matter_key,
        participant_name=name,
        email_address=email_address,
        is_active=True,
    )
    db.add(p)
    # Don't commit - let the test framework handle it
    db.flush()  # Generate ID without committing
    return p


def _seed_email(
    db,
    client=None,
    sender="sender@example.com",
    to_recipients=None,
    cc_recipients=None,
    matter_key=None,
    processing_status="RECEIVED",
):
    from app.models.email import Email
    eid = uuid.uuid4()
    row = Email(
        email_id=eid,
        message_id=f"<test-{eid}@example.com>",
        matter_key=matter_key,
        sender=sender,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        subject="Test subject",
        body_text="Test body",
        raw_file_path=f"data/emails/ingested/{eid}.eml",
        content_hash=uuid.uuid4().hex,
        processing_status=processing_status,
    )
    db.add(row)
    # Don't commit - let the test framework handle it
    db.flush()  # Generate ID without committing
    return row


# ---------------------------------------------------------------------------
# 1. Exact match via sender
# ---------------------------------------------------------------------------
class TestExactSenderMatch:
    def test_resolved_status(self, client, db_session):
        _seed_matter(db_session, client)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, client, sender="spatel@samplelaw.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "resolved"

    def test_matter_key_in_response(self, client, db_session):
        _seed_matter(db_session, client)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, client, sender="spatel@samplelaw.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["matter_key"] == "10001-001"

    def test_match_found_true(self, client, db_session):
        _seed_matter(db_session, client)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, client, sender="spatel@samplelaw.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["match_found"] is True

    def test_processing_status_is_matter_identified(self, client, db_session):
        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["processing_status"] == "MATTER_IDENTIFIED"

    def test_matter_key_written_to_db(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        client.post(f"/api/emails/{email_row.email_id}/resolve")

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == "10001-001"

    def test_processing_status_written_to_db(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        client.post(f"/api/emails/{email_row.email_id}/resolve")

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.processing_status == "MATTER_IDENTIFIED"


# ---------------------------------------------------------------------------
# 2. Match via To recipient
# ---------------------------------------------------------------------------
class TestToRecipientMatch:
    def test_to_recipient_resolves(self, client, db_session):
        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "maya.desai@harborspirits.example")
        email_row = _seed_email(
            db_session,
            sender="outside@other.example",
            to_recipients=[{"name": "Maya Desai", "email": "maya.desai@harborspirits.example"}],
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["status"] == "resolved"
        assert resp.json()["matter_key"] == "10001-001"


# ---------------------------------------------------------------------------
# 3. Match via CC recipient
# ---------------------------------------------------------------------------
class TestCCRecipientMatch:
    def test_cc_recipient_resolves(self, client, db_session):
        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "abell@bellmercer.example")
        email_row = _seed_email(
            db_session,
            sender="outside@other.example",
            to_recipients=[{"name": "Other", "email": "other@other.example"}],
            cc_recipients=[{"name": "Anthony Bell", "email": "abell@bellmercer.example"}],
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["status"] == "resolved"
        assert resp.json()["matter_key"] == "10001-001"


# ---------------------------------------------------------------------------
# 4. No match
# ---------------------------------------------------------------------------
class TestNoMatch:
    def test_unresolved_status(self, client, db_session):
        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "known@example.com")
        email_row = _seed_email(db_session, sender="unknown@other.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "unresolved"

    def test_matter_key_remains_null(self, client, db_session):
        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "known@example.com")
        email_row = _seed_email(db_session, sender="unknown@other.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["matter_key"] is None

    def test_match_found_false(self, client, db_session):
        _seed_matter(db_session)
        email_row = _seed_email(db_session, sender="nobody@nowhere.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["match_found"] is False

    def test_processing_status_is_review_required(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session)
        email_row = _seed_email(
            db_session,
            sender="nobody@nowhere.example",
            processing_status="RECEIVED",
        )
        client.post(f"/api/emails/{email_row.email_id}/resolve")

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.processing_status == "REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# 5. Already-resolved email
# ---------------------------------------------------------------------------
class TestAlreadyResolved:
    def test_already_resolved_status(self, client, db_session):
        _seed_matter(db_session)
        email_row = _seed_email(
            db_session,
            sender="spatel@samplelaw.example",
            matter_key="10001-001",
            processing_status="MATTER_IDENTIFIED",
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "already_resolved"

    def test_already_resolved_returns_existing_matter_key(self, client, db_session):
        _seed_matter(db_session)
        email_row = _seed_email(
            db_session,
            sender="spatel@samplelaw.example",
            matter_key="10001-001",
            processing_status="MATTER_IDENTIFIED",
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["matter_key"] == "10001-001"

    def test_already_resolved_no_db_change(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session)
        email_row = _seed_email(
            db_session,
            matter_key="10001-001",
            processing_status="MATTER_IDENTIFIED",
        )
        original_status = email_row.processing_status

        client.post(f"/api/emails/{email_row.email_id}/resolve")

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.processing_status == original_status


# ---------------------------------------------------------------------------
# 6. Ambiguous match (addresses span two Matters)
# ---------------------------------------------------------------------------
class TestAmbiguousMatch:
    def test_ambiguous_is_unresolved(self, client, db_session):
        from app.models.email import Email

        # Two matters
        _seed_matter(db_session, client, "10001-001")
        _seed_matter(db_session, client, "10002-001")
        # Each has a different participant with the same email address
        # Actually: one address maps to matter A, another to matter B
        _seed_participant(db_session, "10001-001", "alice@example.com")
        _seed_participant(db_session, "10002-001", "bob@example.com")

        # Email has addresses that match both matters
        email_row = _seed_email(
            db_session,
            client,
            sender="alice@example.com",
            to_recipients=[{"name": "Bob", "email": "bob@example.com"}],
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["status"] == "unresolved"
        assert resp.json()["matter_key"] is None

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.processing_status == "REVIEW_REQUIRED"
        assert updated.matter_key is None


# ---------------------------------------------------------------------------
# 7. Unknown email_id → 404
# ---------------------------------------------------------------------------
class TestUnknownEmailId:
    def test_returns_404(self, client, db_session):
        fake_id = uuid.uuid4()
        resp = client.post(f"/api/emails/{fake_id}/resolve")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_uuid_returns_422(self, client, db_session):
        resp = client.post("/api/emails/not-a-uuid/resolve")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 8. CaseBrainLog creation on successful manual resolution
# ---------------------------------------------------------------------------
class TestManualResolutionCaseBrainLog:
    def test_successful_resolution_creates_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "resolved"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_successful_resolution_creates_exactly_one_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        client.post(f"/api/emails/{email_row.email_id}/resolve")
        client.post(f"/api/emails/{email_row.email_id}/resolve")

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_repeating_resolution_does_not_create_duplicate_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        resp1 = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp1.json()["status"] == "resolved"

        resp2 = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp2.json()["status"] == "already_resolved"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_already_resolved_does_not_create_duplicate_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        email_row = _seed_email(
            db_session,
            sender="spatel@samplelaw.example",
            matter_key="10001-001",
            processing_status="MATTER_IDENTIFIED",
        )

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["status"] == "already_resolved"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_no_match_creates_no_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "known@example.com")
        email_row = _seed_email(db_session, sender="unknown@other.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["status"] == "unresolved"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_ambiguous_creates_no_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session, client, "10001-001")
        _seed_matter(db_session, client, "10002-001")
        _seed_participant(db_session, "10001-001", "alice@example.com")
        _seed_participant(db_session, "10002-001", "bob@example.com")

        email_row = _seed_email(
            db_session,
            client,
            sender="alice@example.com",
            to_recipients=[{"name": "Bob", "email": "bob@example.com"}],
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.json()["status"] == "unresolved"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_successful_resolution_email_state_is_correct(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        client.post(f"/api/emails/{email_row.email_id}/resolve")

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == "10001-001"
        assert updated.processing_status == "MATTER_IDENTIFIED"

    def test_successful_resolution_case_brain_log_fields(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        client.post(f"/api/emails/{email_row.email_id}/resolve")

        log = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).one()
        assert log.matter_key == "10001-001"
        assert log.email_id == email_row.email_id
        assert log.source_type == "EMAIL"
        assert log.source_reference == email_row.message_id
        assert log.source_actor == "spatel@samplelaw.example"
        assert "10001-001" in log.update_summary
        assert log.logged_by is None

    def test_non_existent_email_still_returns_404(self, client, db_session):
        fake_id = uuid.uuid4()
        resp = client.post(f"/api/emails/{fake_id}/resolve")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 9. REVIEW_REQUIRED workflow tests
# ---------------------------------------------------------------------------
class TestReviewRequiredWorkflow:
    def test_no_match_sets_review_required(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "known@example.com")
        email_row = _seed_email(db_session, sender="unknown@other.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "unresolved"
        assert resp.json()["match_found"] is False
        assert resp.json()["matter_key"] is None
        assert resp.json()["processing_status"] == "REVIEW_REQUIRED"

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key is None
        assert updated.processing_status == "REVIEW_REQUIRED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_no_usable_addresses_sets_review_required(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        email_row = _seed_email(db_session, sender="")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "unresolved"
        assert resp.json()["processing_status"] == "REVIEW_REQUIRED"
        assert resp.json()["matter_key"] is None

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key is None
        assert updated.processing_status == "REVIEW_REQUIRED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_ambiguous_sets_review_required(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session, client, "10001-001")
        _seed_matter(db_session, client, "10002-001")
        _seed_participant(db_session, "10001-001", "alice@example.com")
        _seed_participant(db_session, "10002-001", "bob@example.com")

        email_row = _seed_email(
            db_session,
            client,
            sender="alice@example.com",
            to_recipients=[{"name": "Bob", "email": "bob@example.com"}],
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "unresolved"
        assert resp.json()["match_found"] is False
        assert resp.json()["matter_key"] is None
        assert resp.json()["processing_status"] == "REVIEW_REQUIRED"

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key is None
        assert updated.processing_status == "REVIEW_REQUIRED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_successful_resolution_creates_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "resolved"
        assert resp.json()["matter_key"] == "10001-001"
        assert resp.json()["processing_status"] == "MATTER_IDENTIFIED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_repeated_resolution_creates_exactly_one_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        resp1 = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp1.json()["status"] == "resolved"

        resp2 = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp2.json()["status"] == "already_resolved"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_manual_resolution_after_review_required(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")
        email_row = _seed_email(db_session, sender="spatel@samplelaw.example")

        # First resolution — should succeed
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "resolved"
        assert resp.json()["matter_key"] == "10001-001"
        assert resp.json()["processing_status"] == "MATTER_IDENTIFIED"

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == "10001-001"
        assert updated.processing_status == "MATTER_IDENTIFIED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_manual_resolution_still_unresolved(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "known@example.com")
        email_row = _seed_email(db_session, sender="unknown@other.example")

        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "unresolved"
        assert resp.json()["processing_status"] == "REVIEW_REQUIRED"
        assert resp.json()["matter_key"] is None

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key is None
        assert updated.processing_status == "REVIEW_REQUIRED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_manual_resolution_ambiguous(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session, client, "10001-001")
        _seed_matter(db_session, client, "10002-001")
        _seed_participant(db_session, "10001-001", "alice@example.com")
        _seed_participant(db_session, "10002-001", "bob@example.com")

        email_row = _seed_email(
            db_session,
            client,
            sender="alice@example.com",
            to_recipients=[{"name": "Bob", "email": "bob@example.com"}],
        )
        resp = client.post(f"/api/emails/{email_row.email_id}/resolve")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "unresolved"
        assert resp.json()["processing_status"] == "REVIEW_REQUIRED"
        assert resp.json()["matter_key"] is None

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key is None
        assert updated.processing_status == "REVIEW_REQUIRED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0

    def test_ingestion_no_match_persists_review_required(self, client, db_session):
        from app.models.email import Email
        from app.models.case_brain_log import CaseBrainLog

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "known@example.com")

        NO_MATCH_EML = (
            b"From: unknown@example.com\r\n"
            b"To: other@example.com\r\n"
            b"Subject: No Match\r\n"
            b"Date: Mon, 11 Aug 2026 09:00:00 -0400\r\n"
            b"Message-ID: <no-match-review-001@example.com>\r\n"
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/plain; charset=\"utf-8\"\r\n"
            b"\r\n"
            b"No match body.\r\n"
        )

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", NO_MATCH_EML, "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["processing_status"] == "REVIEW_REQUIRED"

        email_id = resp.json()["email_id"]
        db_session.expire_all()
        updated = db_session.get(Email, email_id)
        assert updated.matter_key is None
        assert updated.processing_status == "REVIEW_REQUIRED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_id).all()
        assert len(logs) == 0

    def test_ingestion_successful_resolution_creates_case_brain_log(self, client, db_session):
        from app.models.case_brain_log import CaseBrainLog
        from app.models.email import Email

        _seed_matter(db_session)
        _seed_participant(db_session, "10001-001", "spatel@samplelaw.example")

        MATCHING_EML = (
            b"From: spatel@samplelaw.example\r\n"
            b"To: other@example.com\r\n"
            b"Subject: Test\r\n"
            b"Date: Mon, 11 Aug 2026 09:00:00 -0400\r\n"
            b"Message-ID: <ingest-review-001@example.com>\r\n"
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/plain; charset=\"utf-8\"\r\n"
            b"\r\n"
            b"Test body.\r\n"
        )

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MATCHING_EML, "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["processing_status"] == "MATTER_IDENTIFIED"

        email_id = resp.json()["email_id"]
        db_session.expire_all()
        updated = db_session.get(Email, email_id)
        assert updated.matter_key == "10001-001"
        assert updated.processing_status == "MATTER_IDENTIFIED"

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_id).all()
        assert len(logs) == 1
