"""
Tests for the Email Detail endpoint.

Coverage:
  1. Existing email returns 200
  2. Returned email_id is correct
  3. Returned message_id is correct
  4. Returned matter_key is correct
  5. Sender is correct
  6. Recipients are returned correctly
  7. Subject is correct
  8. Body text is returned correctly
  9. Processing status is correct
  10. Raw file path is returned correctly
  11. Non-existent email returns 404
  12. Endpoint is read-only and does not create/update CaseBrainLog records
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter


def _seed_matter(db, matter_key: str | None = None):
    if matter_key is None:
        matter_key = f"TEST-DETAIL-{uuid.uuid4().hex[:8]}"
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for email detail tests",
        matter_status="open",
    )
    db.add(m)
    db.flush()
    return m


def _seed_email(
    db,
    matter_key: str | None = None,
    email_id: uuid.UUID | None = None,
    sender: str = "sender@example.com",
    to_recipients=None,
    cc_recipients=None,
    subject: str = "Test subject",
    body_text: str = "Test body",
    processing_status: str = "RECEIVED",
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
        body_text=body_text,
        received_at=None,
        raw_file_path=f"data/emails/ingested/{email_id}.eml",
        content_hash=uuid.uuid4().hex,
        processing_status=processing_status,
    )
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------------------
# 1. Existing email returns 200
# ---------------------------------------------------------------------------
class TestEmailDetailExisting:
    def test_returns_200(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-200")
        email_row = _seed_email(db_session, matter_key=matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.status_code == status.HTTP_200_OK

    def test_response_email_id_is_correct(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-ID")
        email_row = _seed_email(db_session, matter_key=matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["email_id"] == str(email_row.email_id)

    def test_response_message_id_is_correct(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-MSGID")
        email_row = _seed_email(db_session, matter_key=matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["message_id"] == f"<test-{email_row.email_id}@example.com>"

    def test_response_matter_key_is_correct(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-MATTER")
        email_row = _seed_email(db_session, matter_key=matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["matter_key"] == matter.matter_key

    def test_response_sender_is_correct(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-SENDER")
        email_row = _seed_email(db_session, matter_key=matter.matter_key, sender="alice@example.com")
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["sender"] == "alice@example.com"

    def test_response_recipients_are_returned(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-RECIP")
        to_recipients = [{"name": "Bob", "email": "bob@example.com"}]
        cc_recipients = [{"name": "Carol", "email": "carol@example.com"}]
        email_row = _seed_email(
            db_session,
            matter_key=matter.matter_key,
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
        )
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        data = resp.json()
        assert data["to_recipients"] == to_recipients
        assert data["cc_recipients"] == cc_recipients

    def test_response_subject_is_correct(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-SUBJECT")
        email_row = _seed_email(db_session, matter_key=matter.matter_key, subject="Hello World")
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["subject"] == "Hello World"

    def test_response_body_text_is_returned(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-BODY")
        email_row = _seed_email(db_session, matter_key=matter.matter_key, body_text="Email body content")
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["body_text"] == "Email body content"

    def test_response_processing_status_is_correct(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-STATUS")
        email_row = _seed_email(db_session, matter_key=matter.matter_key, processing_status="MATTER_IDENTIFIED")
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["processing_status"] == "MATTER_IDENTIFIED"

    def test_response_raw_file_path_is_returned(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-RAW")
        email_row = _seed_email(db_session, matter_key=matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.json()["raw_file_path"] == f"data/emails/ingested/{email_row.email_id}.eml"


# ---------------------------------------------------------------------------
# 11. Non-existent email returns 404
# ---------------------------------------------------------------------------
class TestEmailDetailNonExistent:
    def test_returns_404(self, client):
        fake_id = uuid.uuid4()
        resp = client.get(f"/api/emails/{fake_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "Email not found"


# ---------------------------------------------------------------------------
# 12. Endpoint is read-only and does not create/update CaseBrainLog records
# ---------------------------------------------------------------------------
class TestEmailDetailReadOnly:
    def test_does_not_create_case_brain_log(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-READONLY")
        email_row = _seed_email(db_session, matter_key=matter.matter_key)
        db_session.commit()

        log_count_before = db_session.query(CaseBrainLog).filter(
            CaseBrainLog.email_id == email_row.email_id
        ).count()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.status_code == status.HTTP_200_OK

        log_count_after = db_session.query(CaseBrainLog).filter(
            CaseBrainLog.email_id == email_row.email_id
        ).count()

        assert log_count_before == log_count_after
        assert log_count_after == 0

    def test_does_not_modify_email_record(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-DETAIL-NOMOD")
        email_row = _seed_email(db_session, matter_key=matter.matter_key, subject="Original Subject")
        db_session.commit()

        resp = client.get(f"/api/emails/{email_row.email_id}")
        assert resp.status_code == status.HTTP_200_OK

        db_session.refresh(email_row)
        assert email_row.subject == "Original Subject"
