"""
Tests for the firm-wide Case Brain search endpoint.

GET /api/case-brain
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.matter import Matter


def _seed_matter(db, matter_key: str | None = None, matter_status: str = "open") -> Matter:
    if matter_key is None:
        matter_key = f"TEST-CBS-{uuid.uuid4().hex[:8]}"
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for Case Brain search",
        matter_status=matter_status,
    )
    db.add(m)
    db.flush()
    return m


def _seed_entry(
    db,
    matter_key: str,
    *,
    source_type: str = "manual",
    update_summary: str = "Test entry",
    source_reference: str | None = "ref-001",
    source_actor: str | None = "actor@example.com",
    occurred_at: datetime | None = None,
    logged_by: str | None = "tester",
    email_id: uuid.UUID | None = None,
) -> CaseBrainLog:
    if occurred_at is None:
        occurred_at = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
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
# 1. Empty result / no entries
# ---------------------------------------------------------------------------
class TestEmptyResult:
    def test_returns_200_with_empty_list(self, client, db_session):
        resp = client.get("/api/case-brain")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["total"] == 0
        assert body["entries"] == []


# ---------------------------------------------------------------------------
# 2. Returns entries
# ---------------------------------------------------------------------------
class TestReturnsEntries:
    def test_returns_case_brain_entries(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-200")
        _seed_entry(db_session, matter.matter_key, update_summary="Entry 1")
        _seed_entry(db_session, matter.matter_key, update_summary="Entry 2")
        db_session.commit()

        resp = client.get("/api/case-brain")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["total"] >= 2
        summaries = {e["update_summary"] for e in body["entries"]}
        assert "Entry 1" in summaries
        assert "Entry 2" in summaries


# ---------------------------------------------------------------------------
# 3. Default limit = 50
# ---------------------------------------------------------------------------
class TestDefaultLimit:
    def test_default_limit_is_50(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-LIMIT")
        for i in range(60):
            _seed_entry(db_session, matter.matter_key, update_summary=f"Entry {i}")
        db_session.commit()

        resp = client.get("/api/case-brain")
        assert resp.json()["limit"] == 50
        assert len(resp.json()["entries"]) == 50


# ---------------------------------------------------------------------------
# 4. Custom limit
# ---------------------------------------------------------------------------
class TestCustomLimit:
    def test_custom_limit(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-CLIMIT")
        for i in range(10):
            _seed_entry(db_session, matter.matter_key, update_summary=f"Entry {i}")
        db_session.commit()

        resp = client.get("/api/case-brain?limit=5")
        assert resp.json()["limit"] == 5
        assert len(resp.json()["entries"]) == 5


# ---------------------------------------------------------------------------
# 5. Offset pagination
# ---------------------------------------------------------------------------
class TestOffsetPagination:
    def test_offset_skips_records(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-OFFSET")
        for i in range(10):
            _seed_entry(db_session, matter.matter_key, update_summary=f"Offset {i}")
        db_session.commit()

        resp0 = client.get("/api/case-brain?limit=3&offset=0")
        resp3 = client.get("/api/case-brain?limit=3&offset=3")
        ids0 = {e["brain_entry_id"] for e in resp0.json()["entries"]}
        ids3 = {e["brain_entry_id"] for e in resp3.json()["entries"]}
        assert len(ids0) == 3
        assert len(ids3) == 3
        assert ids0.isdisjoint(ids3)


# ---------------------------------------------------------------------------
# 6. limit below 1 → 422
# ---------------------------------------------------------------------------
class TestLimitValidation:
    def test_limit_zero_returns_422(self, client, db_session):
        resp = client.get("/api/case-brain?limit=0")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_above_200_returns_422(self, client, db_session):
        resp = client.get("/api/case-brain?limit=201")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_200_allowed(self, client, db_session):
        resp = client.get("/api/case-brain?limit=200")
        assert resp.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 7. Negative offset → 422
# ---------------------------------------------------------------------------
class TestOffsetValidation:
    def test_negative_offset_returns_422(self, client, db_session):
        resp = client.get("/api/case-brain?offset=-1")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 8. q search matches update_summary
# ---------------------------------------------------------------------------
class TestQSearch:
    def test_matches_update_summary(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-QSUM")
        _seed_entry(db_session, matter.matter_key, update_summary="Contract review completed")
        _seed_entry(db_session, matter.matter_key, update_summary="Email received")
        db_session.commit()

        resp = client.get("/api/case-brain?q=contract")
        body = resp.json()
        assert body["total"] >= 1
        summaries = [e["update_summary"] for e in body["entries"]]
        assert any("Contract review completed" in s for s in summaries)

    def test_matches_source_reference(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-QREF")
        _seed_entry(db_session, matter.matter_key, source_reference="MSG-2026-001")
        db_session.commit()

        resp = client.get("/api/case-brain?q=MSG-2026-001")
        body = resp.json()
        assert body["total"] >= 1
        assert body["entries"][0]["source_reference"] == "MSG-2026-001"

    def test_matches_source_actor(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-QACT")
        _seed_entry(db_session, matter.matter_key, source_actor="jane.doe@example.com")
        db_session.commit()

        resp = client.get("/api/case-brain?q=jane.doe")
        body = resp.json()
        assert body["total"] >= 1
        assert body["entries"][0]["source_actor"] == "jane.doe@example.com"

    def test_matches_matter_key(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-QMAT")
        _seed_entry(db_session, matter.matter_key, update_summary="Some note")
        db_session.commit()

        resp = client.get("/api/case-brain?q=TEST-CBS-QMAT")
        body = resp.json()
        assert body["total"] >= 1
        assert all(e["matter_key"] == "TEST-CBS-QMAT" for e in body["entries"])

    def test_case_insensitive(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-QCI")
        _seed_entry(db_session, matter.matter_key, update_summary="CONTRACT REVIEW")
        db_session.commit()

        resp = client.get("/api/case-brain?q=contract")
        body = resp.json()
        assert body["total"] >= 1

    def test_whitespace_q_is_no_filter(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-QWS")
        _seed_entry(db_session, matter.matter_key, update_summary="Anything")
        db_session.commit()

        resp = client.get("/api/case-brain?q=%20%20%20")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# 9. source_type filter
# ---------------------------------------------------------------------------
class TestSourceTypeFilter:
    def test_filters_by_source_type(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-ST")
        _seed_entry(db_session, matter.matter_key, source_type="email", update_summary="Email entry")
        _seed_entry(db_session, matter.matter_key, source_type="manual", update_summary="Manual entry")
        db_session.commit()

        resp = client.get("/api/case-brain?source_type=email")
        body = resp.json()
        assert body["total"] >= 1
        assert all(e["source_type"] == "email" for e in body["entries"])

    def test_source_type_case_insensitive(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-STCI")
        _seed_entry(db_session, matter.matter_key, source_type="EMAIL", update_summary="Email entry")
        db_session.commit()

        resp = client.get("/api/case-brain?source_type=email")
        body = resp.json()
        assert body["total"] >= 1
        assert all(e["source_type"] == "EMAIL" for e in body["entries"])

    def test_source_type_filter_accepts_unknown_values(self, client, db_session):
        """Backend does not enforce source_type vocabulary at the DB layer."""
        matter = _seed_matter(db_session, "TEST-CBS-UNKNOWN")
        _seed_entry(db_session, matter.matter_key, source_type="custom", update_summary="Custom source")
        db_session.commit()

        resp = client.get("/api/case-brain?source_type=custom")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# 10. matter_key filter
# ---------------------------------------------------------------------------
class TestMatterKeyFilter:
    def test_filters_by_matter_key(self, client, db_session):
        m1 = _seed_matter(db_session, "TEST-CBS-MK1")
        m2 = _seed_matter(db_session, "TEST-CBS-MK2")
        _seed_entry(db_session, m1.matter_key, update_summary="Entry for m1")
        _seed_entry(db_session, m2.matter_key, update_summary="Entry for m2")
        db_session.commit()

        resp = client.get(f"/api/case-brain?matter_key={m1.matter_key}")
        body = resp.json()
        assert body["total"] >= 1
        assert all(e["matter_key"] == m1.matter_key for e in body["entries"])

    def test_matter_key_case_insensitive(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-MKCI")
        _seed_entry(db_session, matter.matter_key, update_summary="Entry")
        db_session.commit()

        resp = client.get(f"/api/case-brain?matter_key={matter.matter_key.lower()}")
        body = resp.json()
        assert body["total"] >= 1


# ---------------------------------------------------------------------------
# 11. Date filters
# ---------------------------------------------------------------------------
class TestDateFilters:
    def test_date_from_filter(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-DF")
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="Old entry",
            occurred_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="New entry",
            occurred_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        resp = client.get("/api/case-brain?date_from=2026-05-01T00:00:00Z")
        body = resp.json()
        assert body["total"] >= 1
        summaries = [e["update_summary"] for e in body["entries"]]
        assert "New entry" in summaries
        assert "Old entry" not in summaries

    def test_date_to_filter(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-DT")
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="Old entry",
            occurred_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="New entry",
            occurred_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        resp = client.get("/api/case-brain?date_to=2026-05-01T00:00:00Z")
        body = resp.json()
        assert body["total"] >= 1
        summaries = [e["update_summary"] for e in body["entries"]]
        assert "Old entry" in summaries
        assert "New entry" not in summaries

    def test_date_from_and_date_to_combined(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-BOTH")
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="Before",
            occurred_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="Inside",
            occurred_at=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="After",
            occurred_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        resp = client.get(
            "/api/case-brain?date_from=2026-03-01T00:00:00Z&date_to=2026-06-01T00:00:00Z"
        )
        body = resp.json()
        assert body["total"] >= 1
        summaries = [e["update_summary"] for e in body["entries"]]
        assert "Inside" in summaries
        assert "Before" not in summaries
        assert "After" not in summaries


# ---------------------------------------------------------------------------
# 12. AND semantics for multiple filters
# ---------------------------------------------------------------------------
class TestMultipleFilters:
    def test_and_semantics(self, client, db_session):
        m1 = _seed_matter(db_session, "TEST-CBS-AND1")
        m2 = _seed_matter(db_session, "TEST-CBS-AND2")
        _seed_entry(db_session, m1.matter_key, source_type="email", update_summary="Contract")
        _seed_entry(db_session, m2.matter_key, source_type="manual", update_summary="Contract")
        _seed_entry(db_session, m1.matter_key, source_type="manual", update_summary="Contract")
        db_session.commit()

        resp = client.get(
            f"/api/case-brain?q=Contract&source_type=email&matter_key={m1.matter_key}"
        )
        body = resp.json()
        assert body["total"] >= 1
        for entry in body["entries"]:
            assert entry["source_type"] == "email"
            assert entry["matter_key"] == m1.matter_key
            assert "Contract" in entry["update_summary"]


# ---------------------------------------------------------------------------
# 13. total is before pagination
# ---------------------------------------------------------------------------
class TestTotalBeforePagination:
    def test_total_reflects_all_matches(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-TOTAL")
        for i in range(7):
            _seed_entry(db_session, matter.matter_key, update_summary=f"Entry {i}")
        db_session.commit()

        resp = client.get("/api/case-brain?limit=2")
        body = resp.json()
        assert body["total"] == 7
        assert len(body["entries"]) == 2


# ---------------------------------------------------------------------------
# 14. Ordering: newest first
# ---------------------------------------------------------------------------
class TestOrdering:
    def test_newest_first(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-ORD")
        old = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        new = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        _seed_entry(db_session, matter.matter_key, update_summary="Old", occurred_at=old)
        _seed_entry(db_session, matter.matter_key, update_summary="New", occurred_at=new)
        db_session.commit()

        resp = client.get("/api/case-brain?limit=10")
        summaries = [e["update_summary"] for e in resp.json()["entries"]]
        assert "New" in summaries[:3]
        assert "Old" in summaries[-2:]

    def test_tie_broken_by_brain_entry_id_desc(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-TIE")
        t = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        e1 = _seed_entry(db_session, matter.matter_key, update_summary="a", occurred_at=t)
        e2 = _seed_entry(db_session, matter.matter_key, update_summary="b", occurred_at=t)
        db_session.commit()

        resp = client.get("/api/case-brain?limit=10")
        entries = resp.json()["entries"]
        ids = [e["brain_entry_id"] for e in entries if e["update_summary"] in ("a", "b")]
        assert ids == sorted(ids, reverse=True)


# ---------------------------------------------------------------------------
# 15. Response schema fields
# ---------------------------------------------------------------------------
class TestResponseSchema:
    def test_response_fields(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-SCHEMA")
        _seed_entry(
            db_session,
            matter.matter_key,
            update_summary="Schema test",
            source_reference="ref",
            source_actor="actor",
            logged_by="sp",
        )
        db_session.commit()

        resp = client.get("/api/case-brain")
        entry = resp.json()["entries"][0]
        assert "brain_entry_id" in entry
        assert "matter_key" in entry
        assert "email_id" in entry
        assert "occurred_at" in entry
        assert "logged_at" in entry
        assert "source_type" in entry
        assert "source_reference" in entry
        assert "source_actor" in entry
        assert "update_summary" in entry
        assert "logged_by" in entry

    def test_email_id_present(self, client, db_session):
        from app.models.email import Email

        matter = _seed_matter(db_session, "TEST-CBS-EID")
        eid = uuid.uuid4()
        email_row = Email(
            email_id=eid,
            message_id=f"<test-{eid}@example.com>",
            sender="sender@example.com",
            to_recipients=None,
            cc_recipients=None,
            subject="Test",
            body_text="Body",
            received_at=datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc),
            raw_file_path=f"data/emails/ingested/{eid}.eml",
            content_hash=uuid.uuid4().hex,
            processing_status="MATTER_IDENTIFIED",
        )
        db_session.add(email_row)
        db_session.flush()
        _seed_entry(db_session, matter.matter_key, email_id=eid)
        db_session.commit()

        resp = client.get("/api/case-brain")
        entry = resp.json()["entries"][0]
        assert entry["email_id"] == str(eid)

    def test_email_id_null_when_absent(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-EIDNULL")
        _seed_entry(db_session, matter.matter_key, email_id=None)
        db_session.commit()

        resp = client.get("/api/case-brain")
        entry = resp.json()["entries"][0]
        assert entry["email_id"] is None


# ---------------------------------------------------------------------------
# 16. Existing single-matter endpoint unaffected
# ---------------------------------------------------------------------------
class TestSingleMatterEndpointUnaffected:
    def test_single_matter_endpoint_still_works(self, client, db_session):
        matter = _seed_matter(db_session, "TEST-CBS-SINGLE")
        _seed_entry(db_session, matter.matter_key, update_summary="Single matter entry")
        db_session.commit()

        resp = client.get(f"/api/matters/{matter.matter_key}/case-brain")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["matter_key"] == matter.matter_key
        assert resp.json()["total"] >= 1
