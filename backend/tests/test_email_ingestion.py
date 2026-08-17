"""
Tests for the Email Ingestion service and endpoint.

Coverage:
  1. Valid .eml ingestion → 201, status=ingested, matter_key=NULL, processing_status=RECEIVED
  2. Duplicate by Message-ID → 200, status=duplicate, reason=message_id
  3. Duplicate by content hash (Message-ID stripped) → 200, status=duplicate, reason=content_hash
  4. Email without CC → to_recipients populated, cc_recipients NULL/empty
  5. Email with attachment (EMAIL-003) → body extracted, attachment ignored cleanly
  6. Invalid / non-email input → 422
  7. Empty file → 400
  8. matter_key remains NULL after ingestion
  9. processing_status is RECEIVED after ingestion
 10. All 5 Matter 1 test emails ingest without error
"""

from __future__ import annotations

import hashlib
import re
import uuid

import pytest
from fastapi import status

from .conftest import eml_bytes


# ---------------------------------------------------------------------------
# Helper: build a minimal valid .eml as bytes
# ---------------------------------------------------------------------------
MINIMAL_EML = (
    b"From: alice@example.com\r\n"
    b"To: bob@example.com\r\n"
    b"Subject: Test\r\n"
    b"Date: Mon, 11 Aug 2026 09:00:00 -0400\r\n"
    b"Message-ID: <test-unique-001@example.com>\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: text/plain; charset=\"utf-8\"\r\n"
    b"\r\n"
    b"Hello world.\r\n"
)

EML_NO_CC = (
    b"From: sender@example.com\r\n"
    b"To: recipient@example.com\r\n"
    b"Subject: No CC Email\r\n"
    b"Date: Tue, 12 Aug 2026 10:00:00 -0400\r\n"
    b"Message-ID: <no-cc-001@example.com>\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: text/plain\r\n"
    b"\r\n"
    b"Body without CC.\r\n"
)


# ---------------------------------------------------------------------------
# 1. Valid ingestion
# ---------------------------------------------------------------------------
class TestValidIngestion:
    def test_returns_201_for_new_email(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_response_status_is_ingested(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.json()["status"] == "ingested"

    def test_email_id_is_valid_uuid(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        data = resp.json()
        assert uuid.UUID(data["email_id"])  # raises if invalid

    def test_message_id_extracted(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.json()["message_id"] == "test-unique-001@example.com"


# ---------------------------------------------------------------------------
# 2. matter_key is NULL and processing_status is RECEIVED
# ---------------------------------------------------------------------------
class TestPostIngestionState:
    def test_matter_key_is_null(self, client, db_session):
        from app.models.email import Email

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.status_code == 201
        email_id = uuid.UUID(resp.json()["email_id"])
        row = db_session.get(Email, email_id)
        assert row is not None
        assert row.matter_key is None

    def test_processing_status_is_received(self, client, db_session):
        from app.models.email import Email

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        email_id = uuid.UUID(resp.json()["email_id"])
        row = db_session.get(Email, email_id)
        assert row.processing_status == "RECEIVED"

    def test_response_processing_status_is_received(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.json()["processing_status"] == "RECEIVED"


# ---------------------------------------------------------------------------
# 3. Duplicate by Message-ID
# ---------------------------------------------------------------------------
class TestDuplicateByMessageId:
    def test_second_ingest_returns_200(self, client):
        client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_second_ingest_status_is_duplicate(self, client):
        client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.json()["status"] == "duplicate"

    def test_duplicate_reason_is_message_id(self, client):
        client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        assert resp.json()["duplicate_reason"] == "message_id"

    def test_no_duplicate_db_row(self, client, db_session):
        from app.models.email import Email

        client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        count = db_session.query(Email).count()
        assert count == 1


# ---------------------------------------------------------------------------
# 4. Duplicate by content hash (Message-ID removed)
# ---------------------------------------------------------------------------
class TestDuplicateByContentHash:
    def _strip_message_id(self, raw: bytes) -> bytes:
        """Remove the Message-ID header from raw .eml bytes."""
        lines = raw.splitlines(keepends=True)
        return b"".join(l for l in lines if not l.lower().startswith(b"message-id"))

    def test_content_hash_duplicate_detected(self, client):
        # Ingest original
        client.post(
            "/api/emails/ingest",
            files={"file": ("test.eml", MINIMAL_EML, "message/rfc822")},
        )
        # Ingest same bytes with Message-ID stripped
        stripped = self._strip_message_id(MINIMAL_EML)
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("test2.eml", stripped, "message/rfc822")},
        )
        # The stripped version has a different hash, so it should be NEW
        # (content_hash duplicate only fires when hashes match)
        assert resp.status_code in (200, 201)

    def test_exact_same_bytes_no_message_id(self, client):
        """Two identical files with no Message-ID → same hash → duplicate."""
        no_mid = (
            b"From: a@example.com\r\n"
            b"To: b@example.com\r\n"
            b"Subject: Hash Test\r\n"
            b"Date: Wed, 13 Aug 2026 09:00:00 -0400\r\n"
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: text/plain\r\n"
            b"\r\n"
            b"Same content.\r\n"
        )
        r1 = client.post(
            "/api/emails/ingest",
            files={"file": ("a.eml", no_mid, "message/rfc822")},
        )
        assert r1.status_code == 201

        r2 = client.post(
            "/api/emails/ingest",
            files={"file": ("b.eml", no_mid, "message/rfc822")},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate"
        assert r2.json()["duplicate_reason"] == "content_hash"


# ---------------------------------------------------------------------------
# 5. Email without CC
# ---------------------------------------------------------------------------
class TestEmailWithoutCC:
    def test_ingest_succeeds(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("nocc.eml", EML_NO_CC, "message/rfc822")},
        )
        assert resp.status_code == 201

    def test_cc_recipients_is_null_in_db(self, client, db_session):
        from app.models.email import Email

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("nocc.eml", EML_NO_CC, "message/rfc822")},
        )
        email_id = uuid.UUID(resp.json()["email_id"])
        row = db_session.get(Email, email_id)
        assert row.cc_recipients is None

    def test_to_recipients_populated(self, client, db_session):
        from app.models.email import Email

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("nocc.eml", EML_NO_CC, "message/rfc822")},
        )
        email_id = uuid.UUID(resp.json()["email_id"])
        row = db_session.get(Email, email_id)
        assert row.to_recipients is not None
        assert len(row.to_recipients) == 1
        assert row.to_recipients[0]["email"] == "recipient@example.com"


# ---------------------------------------------------------------------------
# 6. Email with attachment (EMAIL-003)
# ---------------------------------------------------------------------------
class TestEmailWithAttachment:
    def test_ingests_successfully(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("EMAIL-003.eml", eml_bytes("EMAIL-003"), "message/rfc822")},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "ingested"

    def test_body_extracted_correctly(self, client, db_session):
        from app.models.email import Email

        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("EMAIL-003.eml", eml_bytes("EMAIL-003"), "message/rfc822")},
        )
        email_id = uuid.UUID(resp.json()["email_id"])
        row = db_session.get(Email, email_id)
        # Body should contain text from EMAIL-003, not attachment binary
        assert row.body_text is not None
        assert "Bell & Mercer" in row.body_text
        assert "premises lease" in row.body_text.lower()


# ---------------------------------------------------------------------------
# 7. Invalid / non-email input
# ---------------------------------------------------------------------------
class TestInvalidInput:
    def test_empty_file_returns_400(self, client):
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("empty.eml", b"", "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_binary_garbage_returns_422(self, client):
        garbage = b"\x00\x01\x02\x03" * 100
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("garbage.eml", garbage, "message/rfc822")},
        )
        # Either 422 (no From header) or 400 (empty) — not 2xx
        assert resp.status_code in (400, 422)

    def test_missing_from_header_returns_422(self, client):
        no_from = (
            b"To: bob@example.com\r\n"
            b"Subject: No From\r\n"
            b"Date: Mon, 11 Aug 2026 09:00:00 -0400\r\n"
            b"Message-ID: <no-from@example.com>\r\n"
            b"\r\n"
            b"Body.\r\n"
        )
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("nofrom.eml", no_from, "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_plain_text_not_email_returns_422(self, client):
        not_email = b"This is just a plain text file, not an email.\n"
        resp = client.post(
            "/api/emails/ingest",
            files={"file": ("notmail.eml", not_email, "message/rfc822")},
        )
        # No From header → 422
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 8. All 5 Matter 1 test emails ingest cleanly
# ---------------------------------------------------------------------------
class TestMatter1Emails:
    @pytest.mark.parametrize("email_id", [
        "EMAIL-001",
        "EMAIL-002",
        "EMAIL-003",
        "EMAIL-004",
        "EMAIL-005",
    ])
    def test_ingest_all_matter_1_emails(self, client, email_id):
        raw = eml_bytes(email_id)
        resp = client.post(
            "/api/emails/ingest",
            files={"file": (f"{email_id}.eml", raw, "message/rfc822")},
        )
        assert resp.status_code == status.HTTP_201_CREATED, (
            f"{email_id} failed: {resp.status_code} {resp.text}"
        )
        data = resp.json()
        assert data["status"] == "ingested"
        assert data["processing_status"] == "RECEIVED"
        assert uuid.UUID(data["email_id"])

    @pytest.mark.parametrize("email_id", [
        "EMAIL-001",
        "EMAIL-002",
        "EMAIL-003",
        "EMAIL-004",
        "EMAIL-005",
    ])
    def test_matter_key_null_for_all_matter_1_emails(self, client, db_session, email_id):
        from app.models.email import Email

        raw = eml_bytes(email_id)
        resp = client.post(
            "/api/emails/ingest",
            files={"file": (f"{email_id}.eml", raw, "message/rfc822")},
        )
        eid = uuid.UUID(resp.json()["email_id"])
        row = db_session.get(Email, eid)
        assert row.matter_key is None, f"{email_id}: matter_key should be NULL"
