"""
Tests for the Review Queue endpoint.

Coverage:
  1. Returns REVIEW_REQUIRED emails
  2. Does not return MATTER_IDENTIFIED emails
  3. Does not return RECEIVED emails
  4. Returns empty list when no review-required emails exist
  5. Returned fields are correct
  6. Multiple REVIEW_REQUIRED emails are returned
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import status

from app.models.email import Email


def _seed_email(
    db,
    email_id: uuid.UUID | None = None,
    sender: str = "sender@example.com",
    to_recipients=None,
    cc_recipients=None,
    subject: str = "Test subject",
    processing_status: str = "REVIEW_REQUIRED",
    matter_key: str | None = None,
    received_at=None,
    created_at=None,
):
    if email_id is None:
        email_id = uuid.uuid4()
    row = Email(
        email_id=email_id,
        message_id=f"<test-{email_id}@example.com>",
        matter_key=matter_key,
        sender=sender,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        subject=subject,
        body_text="Test body",
        received_at=received_at,
        raw_file_path=f"data/emails/ingested/{email_id}.eml",
        content_hash=uuid.uuid4().hex,
        processing_status=processing_status,
        created_at=created_at,
    )
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------------------
# 1. Returns REVIEW_REQUIRED emails
# ---------------------------------------------------------------------------
class TestReviewQueueReturnsReviewRequired:
    def test_returns_review_required_emails(self, client, db_session):
        _seed_email(db_session, processing_status="REVIEW_REQUIRED")
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 1
        assert len(resp.json()["emails"]) == 1

    def test_does_not_return_matter_identified_emails(self, client, db_session):
        _seed_email(db_session, processing_status="MATTER_IDENTIFIED")
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 0
        assert resp.json()["emails"] == []

    def test_does_not_return_received_emails(self, client, db_session):
        _seed_email(db_session, processing_status="RECEIVED")
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 0
        assert resp.json()["emails"] == []

    def test_does_not_return_processing_emails(self, client, db_session):
        _seed_email(db_session, processing_status="PROCESSING")
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 0
        assert resp.json()["emails"] == []


# ---------------------------------------------------------------------------
# 2. Returns empty list when no review-required emails exist
# ---------------------------------------------------------------------------
class TestReviewQueueEmpty:
    def test_returns_empty_when_no_review_required(self, client, db_session):
        _seed_email(db_session, processing_status="MATTER_IDENTIFIED")
        _seed_email(db_session, processing_status="RECEIVED")
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 0
        assert resp.json()["emails"] == []


# ---------------------------------------------------------------------------
# 3. Returned fields are correct
# ---------------------------------------------------------------------------
class TestReviewQueueFields:
    def test_returned_fields_are_correct(self, client, db_session):
        import datetime as dt

        email_uuid = uuid.uuid4()
        to_recipients = [{"name": "Bob", "email": "bob@example.com"}]
        cc_recipients = [{"name": "Carol", "email": "carol@example.com"}]
        received = dt.datetime(2026, 8, 27, 9, 0, 0, tzinfo=dt.timezone.utc)
        _seed_email(
            db_session,
            email_id=email_uuid,
            sender="alice@example.com",
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            subject="Contract Review",
            processing_status="REVIEW_REQUIRED",
            received_at=received,
        )
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total"] == 1
        entry = data["emails"][0]
        assert entry["email_id"] == str(email_uuid)
        assert entry["message_id"] == f"<test-{email_uuid}@example.com>"
        assert entry["sender"] == "alice@example.com"
        assert entry["to_recipients"] == to_recipients
        assert entry["cc_recipients"] == cc_recipients
        assert entry["subject"] == "Contract Review"
        assert dt.datetime.fromisoformat(entry["received_at"]) == received
        assert entry["processing_status"] == "REVIEW_REQUIRED"
        assert entry["matter_key"] is None


# ---------------------------------------------------------------------------
# 4. Multiple REVIEW_REQUIRED emails are returned
# ---------------------------------------------------------------------------
class TestReviewQueueMultiple:
    def test_multiple_review_required_emails_returned(self, client, db_session):
        e1 = _seed_email(db_session, subject="First", processing_status="REVIEW_REQUIRED")
        e2 = _seed_email(db_session, subject="Second", processing_status="REVIEW_REQUIRED")
        e3 = _seed_email(db_session, subject="Third", processing_status="REVIEW_REQUIRED")
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 3
        assert len(resp.json()["emails"]) == 3
        subjects = {e["subject"] for e in resp.json()["emails"]}
        assert subjects == {"First", "Second", "Third"}

    def test_emails_ordered_by_created_at_descending(self, client, db_session):
        import datetime as dt

        t1 = dt.datetime(2026, 8, 27, 8, 0, 0, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 8, 27, 10, 0, 0, tzinfo=dt.timezone.utc)
        t3 = dt.datetime(2026, 8, 27, 9, 0, 0, tzinfo=dt.timezone.utc)
        e1 = _seed_email(db_session, subject="first", processing_status="REVIEW_REQUIRED", received_at=t1, created_at=t1)
        db_session.commit()
        e2 = _seed_email(db_session, subject="second", processing_status="REVIEW_REQUIRED", received_at=t2, created_at=t2)
        db_session.commit()
        e3 = _seed_email(db_session, subject="third", processing_status="REVIEW_REQUIRED", received_at=t3, created_at=t3)
        db_session.commit()

        resp = client.get("/api/emails/review-required")
        entries = resp.json()["emails"]
        assert len(entries) == 3
        assert entries[0]["subject"] == "second"
        assert entries[1]["subject"] == "third"
        assert entries[2]["subject"] == "first"


# ---------------------------------------------------------------------------
# 5. Endpoint is read-only
# ---------------------------------------------------------------------------
class TestReviewQueueReadOnly:
    def test_does_not_modify_records(self, client, db_session):
        _seed_email(db_session, processing_status="REVIEW_REQUIRED")
        _seed_email(db_session, processing_status="MATTER_IDENTIFIED")
        db_session.commit()

        count_before = db_session.query(Email).filter(Email.processing_status == "REVIEW_REQUIRED").count()

        resp = client.get("/api/emails/review-required")
        assert resp.status_code == status.HTTP_200_OK

        count_after = db_session.query(Email).filter(Email.processing_status == "REVIEW_REQUIRED").count()
        assert count_before == count_after
