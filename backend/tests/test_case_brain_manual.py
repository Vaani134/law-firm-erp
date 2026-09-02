"""
Tests for manual Case Brain Entry authoring.

POST /api/matters/{matter_key}/case-brain
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter


def _seed_matter(
    db,
    matter_key: str | None = None,
    matter_status: str = "open",
) -> Matter:
    if matter_key is None:
        matter_key = f"TEST-CBM-{uuid.uuid4().hex[:8]}"
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for manual Case Brain",
        matter_status=matter_status,
    )
    db.add(m)
    db.flush()
    return m


def _seed_email_source_matter(db) -> tuple[Matter, Email]:
    """Create a matter + email + CaseBrainLog via the email-source path."""
    from app.services.case_brain import create_case_brain_log

    matter = _seed_matter(db, "TEST-CBM-EMAIL")
    eid = uuid.uuid4()
    row = Email(
        email_id=eid,
        message_id=f"<test-{eid}@example.com>",
        matter_key=matter.matter_key,
        sender="sender@example.com",
        to_recipients=None,
        cc_recipients=None,
        subject="Source email",
        body_text="Body",
        received_at=datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc),
        raw_file_path=f"data/emails/ingested/{eid}.eml",
        content_hash=uuid.uuid4().hex,
        processing_status="MATTER_IDENTIFIED",
    )
    db.add(row)
    db.flush()
    create_case_brain_log(db, row, matter.matter_key)
    db.commit()
    return matter, row


# ---------------------------------------------------------------------------
# 1. Valid manual entry
# ---------------------------------------------------------------------------
class TestValidManualEntry:
    def test_returns_201(self, client, db_session):
        _seed_matter(db_session, "CBM-201")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-201/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Phone call with client",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# 2. Response fields
# ---------------------------------------------------------------------------
class TestResponseFields:
    def test_response_matter_key(self, client, db_session):
        _seed_matter(db_session, "CBM-FIELDS")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-FIELDS/case-brain",
            json={"source_type": "manual", "update_summary": "Logged note"},
        )
        assert resp.json()["matter_key"] == "CBM-FIELDS"

    def test_response_contains_brain_entry_id(self, client, db_session):
        _seed_matter(db_session, "CBM-FIELDS-ID")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-FIELDS-ID/case-brain",
            json={"source_type": "intake", "update_summary": "Intake narrative"},
        )
        body = resp.json()
        assert isinstance(body["brain_entry_id"], int)
        assert body["brain_entry_id"] > 0

    def test_response_email_id_is_null(self, client, db_session):
        _seed_matter(db_session, "CBM-FIELDS-EMAIL")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-FIELDS-EMAIL/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )
        assert resp.json()["email_id"] is None

    def test_response_contains_timestamps(self, client, db_session):
        _seed_matter(db_session, "CBM-FIELDS-TS")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-FIELDS-TS/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )
        body = resp.json()
        assert "occurred_at" in body and body["occurred_at"] is not None
        assert "logged_at" in body and body["logged_at"] is not None

    def test_response_source_type_echoed(self, client, db_session):
        _seed_matter(db_session, "CBM-FIELDS-ST")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-FIELDS-ST/case-brain",
            json={"source_type": "intake", "update_summary": "Intake"},
        )
        assert resp.json()["source_type"] == "intake"

    def test_response_update_summary_echoed(self, client, db_session):
        _seed_matter(db_session, "CBM-FIELDS-SUM")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-FIELDS-SUM/case-brain",
            json={"source_type": "manual", "update_summary": "A specific note."},
        )
        assert resp.json()["update_summary"] == "A specific note."


# ---------------------------------------------------------------------------
# 3. Entry appears in GET timeline
# ---------------------------------------------------------------------------
class TestEntryAppearsInTimeline:
    def test_appears_in_get_timeline(self, client, db_session):
        _seed_matter(db_session, "CBM-TIMELINE")
        db_session.commit()

        create_resp = client.post(
            "/api/matters/CBM-TIMELINE/case-brain",
            json={
                "source_type": "intake",
                "update_summary": "Client intake narrative",
            },
        )
        new_id = create_resp.json()["brain_entry_id"]

        get_resp = client.get("/api/matters/CBM-TIMELINE/case-brain")
        body = get_resp.json()
        ids = [e["brain_entry_id"] for e in body["entries"]]
        assert new_id in ids
        entry = next(e for e in body["entries"] if e["brain_entry_id"] == new_id)
        assert entry["source_type"] == "intake"
        assert entry["update_summary"] == "Client intake narrative"
        assert entry["email_id"] is None


# ---------------------------------------------------------------------------
# 4-5. update_summary validation
# ---------------------------------------------------------------------------
class TestUpdateSummaryValidation:
    def test_empty_summary_returns_422(self, client, db_session):
        _seed_matter(db_session, "CBM-SUM-EMPTY")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-SUM-EMPTY/case-brain",
            json={"source_type": "manual", "update_summary": ""},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_whitespace_only_summary_returns_422(self, client, db_session):
        _seed_matter(db_session, "CBM-SUM-WS")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-SUM-WS/case-brain",
            json={"source_type": "manual", "update_summary": "   \t\n  "},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_summary_returns_422(self, client, db_session):
        _seed_matter(db_session, "CBM-SUM-MISSING")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-SUM-MISSING/case-brain",
            json={"source_type": "manual"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 6. source_type="email" rejected
# ---------------------------------------------------------------------------
class TestSourceTypeEmailRejected:
    def test_lowercase_email_returns_422(self, client, db_session):
        _seed_matter(db_session, "CBM-ST-EMAIL-LC")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-ST-EMAIL-LC/case-brain",
            json={"source_type": "email", "update_summary": "Should not be allowed"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_uppercase_EMAIL_returns_422(self, client, db_session):
        _seed_matter(db_session, "CBM-ST-EMAIL-UC")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-ST-EMAIL-UC/case-brain",
            json={"source_type": "EMAIL", "update_summary": "Should not be allowed"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 7. Unknown matter
# ---------------------------------------------------------------------------
class TestUnknownMatter:
    def test_returns_404(self, client, db_session):
        resp = client.post(
            "/api/matters/DOES-NOT-EXIST-999/case-brain",
            json={"source_type": "manual", "update_summary": "n/a"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 8-11. Accepted source types
# ---------------------------------------------------------------------------
class TestAcceptedSourceTypes:
    @pytest.mark.parametrize("source_type", ["manual", "intake", "system", "import"])
    def test_accepted(self, client, db_session, source_type):
        _seed_matter(db_session, f"CBM-ST-{source_type.upper()}")
        db_session.commit()

        resp = client.post(
            f"/api/matters/CBM-ST-{source_type.upper()}/case-brain",
            json={"source_type": source_type, "update_summary": f"Note for {source_type}"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["source_type"] == source_type


# ---------------------------------------------------------------------------
# 12-13. occurred_at
# ---------------------------------------------------------------------------
class TestOccurredAt:
    def test_omitted_occurred_at_is_populated(self, client, db_session):
        _seed_matter(db_session, "CBM-OCC-NOW")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-OCC-NOW/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )
        body = resp.json()
        assert body["occurred_at"] is not None

    def test_explicit_occurred_at_preserved(self, client, db_session):
        _seed_matter(db_session, "CBM-OCC-EXPL")
        db_session.commit()

        when = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        resp = client.post(
            "/api/matters/CBM-OCC-EXPL/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Note",
                "occurred_at": when.isoformat(),
            },
        )
        body = resp.json()
        assert datetime.fromisoformat(body["occurred_at"]) == when


# ---------------------------------------------------------------------------
# 14-15. logged_by
# ---------------------------------------------------------------------------
class TestLoggedBy:
    def test_logged_by_preserved(self, client, db_session):
        _seed_matter(db_session, "CBM-LB-PRES")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-LB-PRES/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Note",
                "logged_by": "SP",
            },
        )
        assert resp.json()["logged_by"] == "SP"

    def test_logged_by_omitted_defaults_to_null(self, client, db_session):
        _seed_matter(db_session, "CBM-LB-NULL")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-LB-NULL/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )
        assert resp.json()["logged_by"] is None

    def test_logged_by_explicit_null(self, client, db_session):
        _seed_matter(db_session, "CBM-LB-ENULL")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-LB-ENULL/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Note",
                "logged_by": None,
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["logged_by"] is None


# ---------------------------------------------------------------------------
# 16. source_reference and source_actor preserved
# ---------------------------------------------------------------------------
class TestProvenanceFields:
    def test_source_reference_preserved(self, client, db_session):
        _seed_matter(db_session, "CBM-PROV-REF")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-PROV-REF/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Note",
                "source_reference": "INTAKE-NOTE-001",
            },
        )
        assert resp.json()["source_reference"] == "INTAKE-NOTE-001"

    def test_source_actor_preserved(self, client, db_session):
        _seed_matter(db_session, "CBM-PROV-ACT")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-PROV-ACT/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Note",
                "source_actor": "Sarah Patel",
            },
        )
        assert resp.json()["source_actor"] == "Sarah Patel"

    def test_source_reference_omitted_defaults_to_null(self, client, db_session):
        _seed_matter(db_session, "CBM-PROV-NULL")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-PROV-NULL/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )
        assert resp.json()["source_reference"] is None
        assert resp.json()["source_actor"] is None


# ---------------------------------------------------------------------------
# 17. Two manual entries on the same matter
# ---------------------------------------------------------------------------
class TestMultipleManualEntries:
    def test_two_manual_entries_both_kept(self, client, db_session):
        _seed_matter(db_session, "CBM-MULTI")
        db_session.commit()

        r1 = client.post(
            "/api/matters/CBM-MULTI/case-brain",
            json={"source_type": "manual", "update_summary": "First call"},
        )
        r2 = client.post(
            "/api/matters/CBM-MULTI/case-brain",
            json={"source_type": "manual", "update_summary": "Second call"},
        )
        assert r1.status_code == status.HTTP_201_CREATED
        assert r2.status_code == status.HTTP_201_CREATED
        assert r1.json()["brain_entry_id"] != r2.json()["brain_entry_id"]

        timeline = client.get("/api/matters/CBM-MULTI/case-brain").json()
        summaries = [e["update_summary"] for e in timeline["entries"]]
        assert "First call" in summaries
        assert "Second call" in summaries


# ---------------------------------------------------------------------------
# 18. last_brain_update
# ---------------------------------------------------------------------------
class TestLastBrainUpdate:
    def test_last_brain_update_is_set(self, client, db_session):
        matter = _seed_matter(db_session, "CBM-LBU")
        before = matter.last_brain_update
        db_session.commit()

        assert before is None
        client.post(
            "/api/matters/CBM-LBU/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )

        db_session.expire(matter)
        reloaded = db_session.get(Matter, "CBM-LBU")
        assert reloaded.last_brain_update is not None
        assert reloaded.last_brain_update > datetime(2000, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 19. No Email row created
# ---------------------------------------------------------------------------
class TestNoEmailCreated:
    def test_manual_entry_does_not_create_email(self, client, db_session):
        matter = _seed_matter(db_session, "CBM-NOEML")
        db_session.commit()

        before = db_session.query(Email).count()
        client.post(
            "/api/matters/CBM-NOEML/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )
        after = db_session.query(Email).count()
        assert before == after


# ---------------------------------------------------------------------------
# 20. email_id is None
# ---------------------------------------------------------------------------
class TestEmailIdNone:
    def test_email_id_is_null_in_db(self, client, db_session):
        matter = _seed_matter(db_session, "CBM-EID-NONE")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-EID-NONE/case-brain",
            json={"source_type": "intake", "update_summary": "Intake narrative"},
        )
        new_id = resp.json()["brain_entry_id"]

        db_session.expire_all()
        entry = db_session.get(CaseBrainLog, new_id)
        assert entry is not None
        assert entry.email_id is None


# ---------------------------------------------------------------------------
# 21. Allowed on a closed matter
# ---------------------------------------------------------------------------
class TestAllowedOnClosedMatter:
    def test_allowed_on_closed_matter(self, client, db_session):
        _seed_matter(db_session, "CBM-CLOSED", matter_status="closed")
        db_session.commit()

        resp = client.post(
            "/api/matters/CBM-CLOSED/case-brain",
            json={"source_type": "manual", "update_summary": "Post-closing note"},
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# 22. Email Case Brain behavior unaffected
# ---------------------------------------------------------------------------
class TestEmailCaseBrainUnaffected:
    def test_existing_email_entry_still_present(self, client, db_session):
        matter, email_row = _seed_email_source_matter(db_session)

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        body = resp.json()
        assert body["total"] >= 1
        email_entries = [
            e for e in body["entries"] if e["source_type"] == "EMAIL"
        ]
        assert len(email_entries) == 1
        assert email_entries[0]["email_id"] == str(email_row.email_id)

    def test_adding_manual_entry_does_not_modify_email_entry(self, client, db_session):
        matter, email_row = _seed_email_source_matter(db_session)
        original_summary = "Email received and associated with Matter TEST-CBM-EMAIL"
        original_actor = email_row.sender

        client.post(
            f"/api/matters/{matter.matter_key}/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "Added later",
                "source_actor": "Some Lawyer",
            },
        )

        db_session.expire(email_row)
        reloaded_email = db_session.get(Email, email_row.email_id)
        assert reloaded_email.sender == original_actor

        timeline = client.get(f"/api/matters/{matter.matter_key}/case-brain").json()
        email_entries = [
            e for e in timeline["entries"] if e["source_type"] == "EMAIL"
        ]
        assert len(email_entries) == 1
        assert original_summary in email_entries[0]["update_summary"]

    def test_creating_manual_entry_does_not_create_email(self, client, db_session):
        _seed_email_source_matter(db_session)

        before = (
            db_session.query(Email)
            .filter(Email.matter_key == "TEST-CBM-EMAIL")
            .count()
        )

        client.post(
            "/api/matters/TEST-CBM-EMAIL/case-brain",
            json={"source_type": "manual", "update_summary": "Note"},
        )

        after = (
            db_session.query(Email)
            .filter(Email.matter_key == "TEST-CBM-EMAIL")
            .count()
        )
        assert before == after
        assert before == 1


# ---------------------------------------------------------------------------
# Bonus: ordering of mixed entries
# ---------------------------------------------------------------------------
class TestTimelineOrdering:
    def test_mixed_entries_ordered_by_occurred_at(self, client, db_session):
        _seed_matter(db_session, "CBM-MIX-ORD")
        db_session.commit()

        when_old = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        when_new = datetime(2025, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        r_late = client.post(
            "/api/matters/CBM-MIX-ORD/case-brain",
            json={
                "source_type": "manual",
                "update_summary": "later note",
                "occurred_at": when_new.isoformat(),
            },
        )
        r_early = client.post(
            "/api/matters/CBM-MIX-ORD/case-brain",
            json={
                "source_type": "intake",
                "update_summary": "earlier note",
                "occurred_at": when_old.isoformat(),
            },
        )
        assert r_early.status_code == status.HTTP_201_CREATED
        assert r_late.status_code == status.HTTP_201_CREATED

        timeline = client.get("/api/matters/CBM-MIX-ORD/case-brain").json()
        summaries = [e["update_summary"] for e in timeline["entries"]]
        assert summaries == ["earlier note", "later note"]


# ---------------------------------------------------------------------------
# Real seed-matter: 10001-001 (provided by conftest's session fixture)
# ---------------------------------------------------------------------------
class TestRealSeedMatter:
    def test_can_add_intake_to_real_seed_matter(self, client):
        resp = client.post(
            "/api/matters/10001-001/case-brain",
            json={
                "source_type": "intake",
                "update_summary": "Client is forming Harbor Spirits Holdings LLC.",
                "source_actor": "Sarah Patel",
                "logged_by": "SP",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["matter_key"] == "10001-001"
        assert body["source_type"] == "intake"

        timeline = client.get("/api/matters/10001-001/case-brain").json()
        ids = [e["brain_entry_id"] for e in timeline["entries"]]
        assert body["brain_entry_id"] in ids
