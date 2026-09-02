"""
Tests for manual Matter Assignment.

POST /api/emails/{email_id}/assign-matter
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant


def _seed_matter(db, matter_key: str | None = None):
    from app.models.matter import Matter
    if matter_key is None:
        matter_key = f"TEST-MA-{uuid.uuid4().hex[:8]}"
    
    existing = db.query(Matter).filter(Matter.matter_key == matter_key).first()
    if existing:
        return existing
    
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for assignment tests",
        matter_status="open",
    )
    db.add(m)
    db.flush()
    return m


def _seed_email(
    db,
    email_id: uuid.UUID | None = None,
    sender: str = "sender@example.com",
    matter_key: str | None = None,
    processing_status: str = "REVIEW_REQUIRED",
):
    if email_id is None:
        email_id = uuid.uuid4()
    row = Email(
        email_id=email_id,
        message_id=f"<test-{email_id}@example.com>",
        matter_key=matter_key,
        sender=sender,
        to_recipients=None,
        cc_recipients=None,
        subject="Test subject",
        body_text="Test body",
        received_at=None,
        raw_file_path=f"data/emails/ingested/{email_id}.eml",
        content_hash=uuid.uuid4().hex,
        processing_status=processing_status,
    )
    db.add(row)
    db.flush()
    return row


def _cleanup_test_data(db):
    db.query(CaseBrainLog).delete()
    db.query(Email).delete()
    db.query(MatterParticipant).filter(MatterParticipant.matter_key == "10001-001").delete()
    db.query(Matter).filter(Matter.matter_key == "10001-001").delete()
    db.commit()


# ---------------------------------------------------------------------------
# 1. Successful manual assignment
# ---------------------------------------------------------------------------
class TestSuccessfulAssignment:
    def test_returns_assigned_status(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session)

        resp = client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "assigned"

    def test_email_matter_key_updated(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session)

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == "10001-001"

    def test_processing_status_becomes_matter_identified(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session, processing_status="REVIEW_REQUIRED")

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.processing_status == "MATTER_IDENTIFIED"

    def test_case_brain_log_created(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session)

        resp = client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )
        assert resp.status_code == status.HTTP_200_OK

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 1

    def test_case_brain_log_fields_are_correct(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session, sender="alice@example.com")

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )

        log = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).one()
        assert log.matter_key == "10001-001"
        assert log.email_id == email_row.email_id
        assert log.source_type == "EMAIL"
        assert log.source_reference == f"<test-{email_row.email_id}@example.com>"
        assert log.source_actor == "alice@example.com"
        assert "10001-001" in log.update_summary
        assert "manually associated" in log.update_summary.lower()
        assert log.logged_by is None


# ---------------------------------------------------------------------------
# 2. Idempotent assignment to same Matter
# ---------------------------------------------------------------------------
class TestIdempotentAssignment:
    def test_already_assigned_returns_ok(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session, matter_key="10001-001", processing_status="MATTER_IDENTIFIED")

        resp = client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "already_assigned"

    def test_already_assigned_does_not_create_duplicate_case_brain_log(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session, matter_key="10001-001", processing_status="MATTER_IDENTIFIED")

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0


# ---------------------------------------------------------------------------
# 3. Conflict when email already belongs to another Matter
# ---------------------------------------------------------------------------
class TestConflictAssignment:
    def test_returns_409_conflict(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        _seed_matter(db_session, "10002-001")
        email_row = _seed_email(db_session, matter_key="10001-001", processing_status="MATTER_IDENTIFIED")

        resp = client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10002-001"},
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_conflict_does_not_modify_email(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session, "10001-001")
        _seed_matter(db_session, "10002-001")
        email_row = _seed_email(db_session, matter_key="10001-001", processing_status="MATTER_IDENTIFIED")

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10002-001"},
        )

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == "10001-001"
        assert updated.processing_status == "MATTER_IDENTIFIED"

    def test_conflict_does_not_create_case_brain_log(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        _seed_matter(db_session, "10002-001")
        email_row = _seed_email(db_session, matter_key="10001-001", processing_status="MATTER_IDENTIFIED")

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10002-001"},
        )

        logs = db_session.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).all()
        assert len(logs) == 0


# ---------------------------------------------------------------------------
# 4. Non-existent email returns 404
# ---------------------------------------------------------------------------
class TestNonExistentEmail:
    def test_returns_404(self, client, db_session):
        fake_id = uuid.uuid4()
        resp = client.post(
            f"/api/emails/{fake_id}/assign-matter",
            json={"matter_key": "10001-001"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 5. Non-existent Matter returns 404
# ---------------------------------------------------------------------------
class TestNonExistentMatter:
    def test_returns_404(self, client, db_session):
        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session)

        resp = client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "NON-EXISTENT-999"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 6. Failed assignment does not modify database
# ---------------------------------------------------------------------------
class TestFailedAssignmentNoDbChange:
    def test_conflict_does_not_change_matter_key(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session, "10001-001")
        _seed_matter(db_session, "10002-001")
        email_row = _seed_email(db_session, matter_key="10001-001", processing_status="MATTER_IDENTIFIED")

        original_matter_key = email_row.matter_key
        original_status = email_row.processing_status

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "10002-001"},
        )

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == original_matter_key
        assert updated.processing_status == original_status

    def test_nonexistent_matter_does_not_change_email(self, client, db_session):
        from app.models.email import Email

        _seed_matter(db_session, "10001-001")
        email_row = _seed_email(db_session)

        original_matter_key = email_row.matter_key
        original_status = email_row.processing_status

        client.post(
            f"/api/emails/{email_row.email_id}/assign-matter",
            json={"matter_key": "NON-EXISTENT-999"},
        )

        db_session.expire(email_row)
        updated = db_session.get(Email, email_row.email_id)
        assert updated.matter_key == original_matter_key
        assert updated.processing_status == original_status
