"""
Tests for the Case Brain timeline endpoint.

Coverage:
   A. Existing Matter with one CaseBrainLog entry
   B. Existing Matter with multiple CaseBrainLog entries
   C. Existing Matter with no CaseBrainLog entries
   D. Non-existent Matter
   E. Endpoint does not modify database records
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.matter import Matter


def _seed_matter(db, matter_key: str | None = None):
    if matter_key is None:
        matter_key = f"TEST-CB-{uuid.uuid4().hex[:8]}"
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for CaseBrain timeline",
        matter_status="open",
    )
    db.add(m)
    db.flush()
    return m


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
# A. Existing Matter with one CaseBrainLog entry
# ---------------------------------------------------------------------------
class TestCaseBrainTimelineWithOneEntry:
    def test_returns_200(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-ONE")
        _seed_case_brain_log(db_session, matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.status_code == status.HTTP_200_OK

    def test_response_matter_key(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-ONE-KEY")
        _seed_case_brain_log(db_session, matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.json()["matter_key"] == matter.matter_key

    def test_response_total_is_one(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-ONE-TOTAL")
        _seed_case_brain_log(db_session, matter.matter_key)
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.json()["total"] == 1

    def test_response_entry_fields(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-ONE-FIELDS")
        occurred = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        _seed_case_brain_log(
            db_session,
            matter.matter_key,
            occurred_at=occurred,
            source_type="EMAIL",
            source_reference="ref-123@example.com",
            source_actor="sender@example.com",
            update_summary="Email received and associated with Matter CBL-ONE-FIELDS",
            logged_by=None,
        )
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        data = resp.json()
        entry = data["entries"][0]
        assert entry["brain_entry_id"] is not None
        assert entry["email_id"] is None
        assert datetime.fromisoformat(entry["occurred_at"]) == occurred
        assert entry["source_type"] == "EMAIL"
        assert entry["source_reference"] == "ref-123@example.com"
        assert entry["source_actor"] == "sender@example.com"
        assert entry["update_summary"] == "Email received and associated with Matter CBL-ONE-FIELDS"
        assert entry["logged_by"] is None


# ---------------------------------------------------------------------------
# B. Existing Matter with multiple CaseBrainLog entries
# ---------------------------------------------------------------------------
class TestCaseBrainTimelineWithMultipleEntries:
    def test_returns_all_entries(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-MULTI")
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=datetime(2026, 8, 18, 9, 0, 0, tzinfo=timezone.utc))
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=datetime(2026, 8, 18, 11, 0, 0, tzinfo=timezone.utc))
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc))
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 3
        assert len(resp.json()["entries"]) == 3

    def test_entries_ordered_by_occurred_at_ascending(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-MULTI-ORDER")
        t1 = datetime(2026, 8, 18, 9, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 18, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t1, update_summary="first")
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t2, update_summary="second")
        _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t3, update_summary="third")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        entries = resp.json()["entries"]
        assert entries[0]["update_summary"] == "first"
        assert entries[1]["update_summary"] == "third"
        assert entries[2]["update_summary"] == "second"

    def test_entries_ordered_by_brain_entry_id_when_occurred_at_tied(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-MULTI-TIE")
        t = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        e1 = _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t, update_summary="a")
        e2 = _seed_case_brain_log(db_session, matter.matter_key, occurred_at=t, update_summary="b")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        entries = resp.json()["entries"]
        assert entries[0]["brain_entry_id"] == e1.brain_entry_id
        assert entries[1]["brain_entry_id"] == e2.brain_entry_id


# ---------------------------------------------------------------------------
# C. Existing Matter with no CaseBrainLog entries
# ---------------------------------------------------------------------------
class TestCaseBrainTimelineWithNoEntries:
    def test_returns_200(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-EMPTY")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.status_code == status.HTTP_200_OK

    def test_response_total_is_zero(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-EMPTY-TOTAL")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.json()["total"] == 0

    def test_response_entries_is_empty_list(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-EMPTY-LIST")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.json()["entries"] == []


# ---------------------------------------------------------------------------
# D. Non-existent Matter
# ---------------------------------------------------------------------------
class TestCaseBrainTimelineNonExistentMatter:
    def test_returns_404(self, client):
        resp = client.get("/api/matters/NON-EXISTENT-999/case-brain")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# E. Endpoint does not modify database records
# ---------------------------------------------------------------------------
class TestCaseBrainTimelineReadOnly:
    def test_does_not_modify_records(self, client, db_session):
        matter = _seed_matter(db_session, "CBL-READONLY")
        e1 = _seed_case_brain_log(db_session, matter.matter_key, occurred_at=datetime(2026, 8, 18, 9, 0, 0, tzinfo=timezone.utc))
        db_session.commit()

        # Capture state before request
        count_before = db_session.query(CaseBrainLog).filter(CaseBrainLog.matter_key == matter.matter_key).count()
        summary_before = e1.update_summary

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.status_code == status.HTTP_200_OK

        # Capture state after request
        count_after = db_session.query(CaseBrainLog).filter(CaseBrainLog.matter_key == matter.matter_key).count()
        db_session.refresh(e1)
        summary_after = e1.update_summary

        assert count_before == count_after
        assert summary_before == summary_after
