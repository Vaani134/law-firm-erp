"""
Tests for the Matter Detail endpoint.

Coverage:
   1. Existing Matter returns 200
   2. Non-existent Matter returns 404
   3. Matter information is returned correctly
   4. Participants are returned correctly
   5. Associated emails are returned correctly
   6. Case Brain entries are returned correctly
   7. Emails have deterministic ordering
   8. Case Brain entries follow occurred_at ASC and brain_entry_id ASC tie-breaking
   9. Matter with no participants/emails/case-brain entries returns empty arrays
   10. Endpoint is read-only and does not create or modify database records
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant


def _seed_matter(db, matter_key: str | None = None, **kwargs):
    if matter_key is None:
        matter_key = f"TEST-MD-{uuid.uuid4().hex[:8]}"
    m = Matter(
        matter_key=matter_key,
        client_id=kwargs.get("client_id", "TEST"),
        matter_id=kwargs.get("matter_id", "001"),
        client_name=kwargs.get("client_name", "Test Client LLC"),
        matter_name=kwargs.get("matter_name", "Test Matter"),
        matter_description=kwargs.get("matter_description", "Test matter for Matter Detail tests"),
        matter_status=kwargs.get("matter_status", "open"),
        practice_area=kwargs.get("practice_area"),
        matter_type=kwargs.get("matter_type"),
        matter_aliases_identifiers=kwargs.get("matter_aliases_identifiers"),
        primary_attorney=kwargs.get("primary_attorney"),
    )
    db.add(m)
    db.flush()
    return m


def _seed_participant(
    db,
    matter_key: str,
    participant_name: str = "Test Participant",
    email_address: str | None = "participant@example.com",
    organization: str | None = "Test Org",
    role_relationship: str | None = "client",
    is_active: bool = True,
):
    p = MatterParticipant(
        matter_key=matter_key,
        participant_name=participant_name,
        email_address=email_address,
        organization=organization,
        role_relationship=role_relationship,
        is_active=is_active,
    )
    db.add(p)
    db.flush()
    return p


def _seed_email(
    db,
    matter_key: str,
    email_id: uuid.UUID | None = None,
    sender: str = "sender@example.com",
    to_recipients=None,
    cc_recipients=None,
    subject: str = "Test subject",
    body_text: str = "Test body",
    processing_status: str = "RECEIVED",
    created_at: datetime | None = None,
):
    if email_id is None:
        email_id = uuid.uuid4()
    if created_at is None:
        created_at = datetime.now(timezone.utc)
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
        created_at=created_at,
    )
    db.add(row)
    db.flush()
    return row


def _seed_case_brain_log(
    db,
    matter_key: str,
    email_id: uuid.UUID | None = None,
    occurred_at: datetime | None = None,
    source_type: str = "EMAIL",
    source_reference: str | None = "msg-001@example.com",
    source_actor: str | None = "actor@example.com",
    update_summary: str = "Test log entry",
    logged_by: str | None = None,
):
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)
    entry = CaseBrainLog(
        matter_key=matter_key,
        email_id=email_id,
        occurred_at=occurred_at,
        source_type=source_type,
        source_reference=source_reference,
        source_actor=source_actor,
        update_summary=update_summary,
        logged_by=logged_by,
    )
    db.add(entry)
    db.flush()
    return entry


# ---------------------------------------------------------------------------
# 1. Existing Matter returns 200
# ---------------------------------------------------------------------------
class TestMatterDetailExisting:
    def test_returns_200(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-200")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        assert resp.status_code == status.HTTP_200_OK

    def test_response_matter_key(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-KEY")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        assert resp.json()["matter"]["matter_key"] == matter.matter_key

    def test_response_matter_fields(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-FIELDS")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        data = resp.json()
        m = data["matter"]
        assert m["client_id"] == "TEST"
        assert m["matter_id"] == "001"
        assert m["client_name"] == "Test Client LLC"
        assert m["matter_name"] == "Test Matter"
        assert m["matter_description"] == "Test matter for Matter Detail tests"
        assert m["matter_status"] == "open"


# ---------------------------------------------------------------------------
# 2. Non-existent Matter returns 404
# ---------------------------------------------------------------------------
class TestMatterDetailNonExistent:
    def test_returns_404(self, client):
        resp = client.get("/api/matters/NON-EXISTENT-999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "Matter not found"


# ---------------------------------------------------------------------------
# 3. Matter information is returned correctly
# ---------------------------------------------------------------------------
class TestMatterDetailMatterInfo:
    def test_matter_fields_populated(self, client, db_session):
        matter = _seed_matter(
            db_session,
            "TEST-MD-INFO",
            client_id="C1",
            matter_id="M1",
            client_name="Client One",
            matter_name="Matter One",
            matter_description="Description",
            matter_status="pending",
            practice_area="Litigation",
            matter_type="Contract",
            matter_aliases_identifiers="alias1, alias2",
            primary_attorney="John Doe",
        )
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        m = resp.json()["matter"]
        assert m["client_id"] == "C1"
        assert m["matter_id"] == "M1"
        assert m["client_name"] == "Client One"
        assert m["matter_name"] == "Matter One"
        assert m["matter_description"] == "Description"
        assert m["matter_status"] == "pending"
        assert m["practice_area"] == "Litigation"
        assert m["matter_type"] == "Contract"
        assert m["matter_aliases_identifiers"] == "alias1, alias2"
        assert m["primary_attorney"] == "John Doe"


# ---------------------------------------------------------------------------
# 4. Participants are returned correctly
# ---------------------------------------------------------------------------
class TestMatterDetailParticipants:
    def test_returns_participants(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-PART")
        p1 = _seed_participant(db_session, matter.matter_key, participant_name="Alice", email_address="alice@example.com")
        p2 = _seed_participant(db_session, matter.matter_key, participant_name="Bob", email_address="bob@example.com")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        participants = resp.json()["participants"]
        assert len(participants) == 2
        names = {p["participant_name"] for p in participants}
        assert names == {"Alice", "Bob"}

    def test_participant_fields_populated(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-PART-FIELDS")
        _seed_participant(
            db_session,
            matter.matter_key,
            participant_name="Carol",
            email_address="carol@example.com",
            organization="Acme Corp",
            role_relationship="client",
            is_active=True,
        )
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        p = resp.json()["participants"][0]
        assert p["participant_name"] == "Carol"
        assert p["email_address"] == "carol@example.com"
        assert p["organization"] == "Acme Corp"
        assert p["role_relationship"] == "client"
        assert p["is_active"] is True

    def test_no_participants_returns_empty_list(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-NOPART")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        assert resp.json()["participants"] == []


# ---------------------------------------------------------------------------
# 5. Associated emails are returned correctly
# ---------------------------------------------------------------------------
class TestMatterDetailEmails:
    def test_returns_emails(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-EMAILS")
        e1 = _seed_email(db_session, matter.matter_key, subject="Email 1")
        e2 = _seed_email(db_session, matter.matter_key, subject="Email 2")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        emails = resp.json()["emails"]
        assert len(emails) == 2
        subjects = {e["subject"] for e in emails}
        assert subjects == {"Email 1", "Email 2"}

    def test_email_fields_populated(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-EMAIL-FIELDS")
        e1 = _seed_email(db_session, matter.matter_key, sender="alice@example.com", subject="Hello")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        e = resp.json()["emails"][0]
        assert e["email_id"] == str(e1.email_id)
        assert e["sender"] == "alice@example.com"
        assert e["subject"] == "Hello"
        assert e["processing_status"] == "RECEIVED"

    def test_no_emails_returns_empty_list(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-NOEMAIL")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        assert resp.json()["emails"] == []


# ---------------------------------------------------------------------------
# 6. Case Brain entries are returned correctly
# ---------------------------------------------------------------------------
class TestMatterDetailCaseBrain:
    def test_returns_case_brain_entries(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-CB")
        e1 = _seed_email(db_session, matter.matter_key)
        _seed_case_brain_log(db_session, matter.matter_key, email_id=e1.email_id, update_summary="Entry 1")
        _seed_case_brain_log(db_session, matter.matter_key, update_summary="Entry 2")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        entries = resp.json()["case_brain"]
        assert len(entries) == 2
        summaries = {entry["update_summary"] for entry in entries}
        assert summaries == {"Entry 1", "Entry 2"}

    def test_case_brain_fields_populated(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-CB-FIELDS")
        e1 = _seed_email(db_session, matter.matter_key)
        occurred = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        _seed_case_brain_log(
            db_session,
            matter.matter_key,
            email_id=e1.email_id,
            occurred_at=occurred,
            source_type="EMAIL",
            source_reference="ref-123@example.com",
            source_actor="actor@example.com",
            update_summary="Summary text",
        )
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        entry = resp.json()["case_brain"][0]
        assert entry["source_type"] == "EMAIL"
        assert entry["source_reference"] == "ref-123@example.com"
        assert entry["source_actor"] == "actor@example.com"
        assert entry["update_summary"] == "Summary text"

    def test_no_case_brain_returns_empty_list(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-NOCB")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        assert resp.json()["case_brain"] == []


# ---------------------------------------------------------------------------
# 7. Emails have deterministic ordering
# ---------------------------------------------------------------------------
class TestMatterDetailEmailOrdering:
    def test_emails_ordered_by_created_at_ascending(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-EMAIL-ORDER")
        t1 = datetime(2026, 8, 18, 9, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 18, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        e1 = _seed_email(db_session, matter.matter_key, created_at=t1, subject="first")
        e2 = _seed_email(db_session, matter.matter_key, created_at=t2, subject="second")
        e3 = _seed_email(db_session, matter.matter_key, created_at=t3, subject="third")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        emails = resp.json()["emails"]
        assert emails[0]["subject"] == "first"
        assert emails[1]["subject"] == "third"
        assert emails[2]["subject"] == "second"

    def test_emails_ordered_by_email_id_when_created_at_tied(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-EMAIL-TIE")
        t = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        e1 = _seed_email(db_session, matter.matter_key, created_at=t, subject="a")
        e2 = _seed_email(db_session, matter.matter_key, created_at=t, subject="b")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        emails = resp.json()["emails"]
        # When created_at is tied, order must be deterministic by email_id ASC
        assert len(emails) == 2
        ids = [e["email_id"] for e in emails]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# 8. Case Brain entries follow occurred_at ASC and brain_entry_id ASC tie-breaking
# ---------------------------------------------------------------------------
class TestMatterDetailCaseBrainOrdering:
    def test_case_brain_ordered_by_occurred_at_ascending(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-CB-ORDER")
        t1 = datetime(2026, 8, 18, 9, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 18, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t1, update_summary="first")
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t2, update_summary="second")
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t3, update_summary="third")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        entries = resp.json()["case_brain"]
        assert entries[0]["update_summary"] == "first"
        assert entries[1]["update_summary"] == "third"
        assert entries[2]["update_summary"] == "second"

    def test_case_brain_ordered_by_brain_entry_id_when_occurred_at_tied(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-CB-TIE")
        t = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        e1 = _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t, update_summary="a")
        e2 = _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t, update_summary="b")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        entries = resp.json()["case_brain"]
        assert entries[0]["brain_entry_id"] == e1.brain_entry_id
        assert entries[1]["brain_entry_id"] == e2.brain_entry_id


# ---------------------------------------------------------------------------
# 9. Matter with no participants/emails/case-brain entries returns empty arrays
# ---------------------------------------------------------------------------
class TestMatterDetailEmptyCollections:
    def test_returns_empty_arrays(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-EMPTY")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}")
        data = resp.json()
        assert data["participants"] == []
        assert data["emails"] == []
        assert data["case_brain"] == []


# ---------------------------------------------------------------------------
# 10. Endpoint is read-only and does not create or modify database records
# ---------------------------------------------------------------------------
class TestMatterDetailReadOnly:
    def test_does_not_modify_records(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-MD-READONLY")
        p1 = _seed_participant(db_session, matter.matter_key, participant_name="Alice")
        e1 = _seed_email(db_session, matter.matter_key, subject="Original")
        _seed_case_brain_log(db_session, matter.matter_key, update_summary="Original log")
        db_session.commit()

        # Capture state before request
        participant_count_before = db_session.query(MatterParticipant).filter(
            MatterParticipant.matter_key == matter.matter_key
        ).count()
        email_count_before = db_session.query(Email).filter(Email.matter_key == matter.matter_key).count()
        cb_count_before = db_session.query(CaseBrainLog).filter(
            CaseBrainLog.matter_key == matter.matter_key
        ).count()
        matter_updated_at_before = matter.updated_at

        resp = client.get(f"/api/matters/{matter.matter_key}")
        assert resp.status_code == status.HTTP_200_OK

        # Capture state after request
        participant_count_after = db_session.query(MatterParticipant).filter(
            MatterParticipant.matter_key == matter.matter_key
        ).count()
        email_count_after = db_session.query(Email).filter(Email.matter_key == matter.matter_key).count()
        cb_count_after = db_session.query(CaseBrainLog).filter(
            CaseBrainLog.matter_key == matter.matter_key
        ).count()
        db_session.refresh(matter)
        matter_updated_at_after = matter.updated_at

        assert participant_count_before == participant_count_after
        assert email_count_before == email_count_after
        assert cb_count_before == cb_count_after
        assert matter_updated_at_before == matter_updated_at_after
