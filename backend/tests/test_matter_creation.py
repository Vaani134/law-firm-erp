"""
Tests for Matter Creation (Intake) endpoint.

POST /api/matters
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import status

from app.models.case_brain_log import CaseBrainLog
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant


def _mk_key(prefix: str = "TEST-MC") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _build_body(**overrides) -> dict:
    """Build a minimal valid MatterCreateRequest body dict."""
    base = {
        "matter_key": _mk_key(),
        "client_id": "TEST",
        "matter_id": "001",
        "client_name": "Test Client LLC",
        "matter_name": "Test Matter",
        "matter_description": "Test matter description",
        "matter_status": "open",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Successful minimal Matter creation
# ---------------------------------------------------------------------------
class TestSuccessfulCreation:
    def test_returns_201(self, client, db_session):
        body = _build_body()
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_response_contains_matter_key(self, client, db_session):
        body = _build_body()
        resp = client.post("/api/matters", json=body)
        assert resp.json()["matter_key"] == body["matter_key"]

    def test_matter_persists_in_database(self, client, db_session):
        body = _build_body()
        client.post("/api/matters", json=body)
        db_session.commit()
        m = db_session.get(Matter, body["matter_key"])
        assert m is not None
        assert m.client_name == "Test Client LLC"


# ---------------------------------------------------------------------------
# 2. Successful creation with optional fields
# ---------------------------------------------------------------------------
class TestCreationWithOptionalFields:
    def test_all_optional_fields(self, client, db_session):
        body = _build_body(
            practice_area="Litigation",
            matter_type="Contract",
            matter_aliases_identifiers="alias1, alias2",
            primary_attorney="Jane Doe",
        )
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["practice_area"] == "Litigation"
        assert data["matter_type"] == "Contract"
        assert data["matter_aliases_identifiers"] == "alias1, alias2"
        assert data["primary_attorney"] == "Jane Doe"


# ---------------------------------------------------------------------------
# 3. Duplicate matter_key
# ---------------------------------------------------------------------------
class TestDuplicateMatterKey:
    def test_duplicate_matter_key_returns_409(self, client, db_session):
        body = _build_body()
        client.post("/api/matters", json=body)
        db_session.commit()

        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# 4. Invalid matter_status
# ---------------------------------------------------------------------------
class TestInvalidStatus:
    def test_invalid_status_returns_422(self, client, db_session):
        body = _build_body(matter_status="not_a_real_status")
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 5. Participant creation
# ---------------------------------------------------------------------------
class TestParticipantCreation:
    def test_participants_created(self, client, db_session):
        body = _build_body(
            participants=[
                {
                    "participant_name": "Alice",
                    "email_address": "alice@example.com",
                    "organization": "Acme Corp",
                    "role_relationship": "client",
                    "is_active": True,
                },
                {
                    "participant_name": "Bob",
                    "email_address": "bob@example.com",
                    "organization": "Beta Inc",
                    "role_relationship": "opposing_counsel",
                },
            ]
        )
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert len(data["participants"]) == 2
        names = {p["participant_name"] for p in data["participants"]}
        assert names == {"Alice", "Bob"}

    def test_empty_participants_list_creates_none(self, client, db_session):
        body = _build_body(participants=[])
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["participants"] == []

    def test_no_participants_key_creates_none(self, client, db_session):
        body = _build_body()
        # participants is not in the body by default
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["participants"] == []


# ---------------------------------------------------------------------------
# 6. Intake Case Brain entry created
# ---------------------------------------------------------------------------
class TestIntakeCaseBrain:
    def test_intake_narrative_creates_case_brain_entry(self, client, db_session):
        body = _build_body(
            intake_narrative={
                "update_summary": "Client intake narrative",
                "source_actor": "Sarah Patel",
                "source_reference": "INTAKE-001",
            }
        )
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert len(data["case_brain_entries"]) == 1
        entry = data["case_brain_entries"][0]
        assert entry["source_type"] == "intake"
        assert entry["update_summary"] == "Client intake narrative"
        assert entry["source_actor"] == "Sarah Patel"
        assert entry["source_reference"] == "INTAKE-001"
        assert entry["email_id"] is None

    def test_no_intake_narrative_creates_no_case_brain_entry(self, client, db_session):
        body = _build_body()
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["case_brain_entries"] == []


# ---------------------------------------------------------------------------
# 7. Participants + intake narrative together
# ---------------------------------------------------------------------------
class TestParticipantsWithIntake:
    def test_both_created_together(self, client, db_session):
        body = _build_body(
            participants=[
                {"participant_name": "Client", "email_address": "client@example.com"}
            ],
            intake_narrative={"update_summary": "Intake note"},
        )
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert len(data["participants"]) == 1
        assert len(data["case_brain_entries"]) == 1
        assert data["case_brain_entries"][0]["source_type"] == "intake"


# ---------------------------------------------------------------------------
# 8. Atomicity — failed transaction rolls back
# ---------------------------------------------------------------------------
class TestAtomicity:
    def test_rollback_on_duplicate_key(self, client, db_session):
        key = _mk_key()
        body1 = _build_body(matter_key=key)
        body2 = _build_body(matter_key=key)

        r1 = client.post("/api/matters", json=body1)
        assert r1.status_code == status.HTTP_201_CREATED

        r2 = client.post("/api/matters", json=body2)
        assert r2.status_code == status.HTTP_409_CONFLICT

        db_session.commit()
        count = db_session.query(Matter).filter(Matter.matter_key == key).count()
        assert count == 1


# ---------------------------------------------------------------------------
# 9. Validation errors
# ---------------------------------------------------------------------------
class TestValidation:
    def test_empty_matter_key_returns_422(self, client, db_session):
        body = _build_body(matter_key="")
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_empty_client_name_returns_422(self, client, db_session):
        body = _build_body(client_name="")
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_required_field_returns_422(self, client, db_session):
        body = _build_body()
        del body["matter_description"]
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 10. Newly-created Matter retrievable via detail
# ---------------------------------------------------------------------------
class TestRetrievableAfterCreation:
    def test_get_matter_detail_after_creation(self, client, db_session):
        body = _build_body(
            matter_key=_mk_key("DETAIL"),
            client_name="Detail Client",
            matter_name="Detail Matter",
        )
        create_resp = client.post("/api/matters", json=body)
        assert create_resp.status_code == status.HTTP_201_CREATED
        key = create_resp.json()["matter_key"]

        resp = client.get(f"/api/matters/{key}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["matter"]["matter_key"] == key
        assert resp.json()["matter"]["client_name"] == "Detail Client"


# ---------------------------------------------------------------------------
# 11. Newly-created Matter appears in search
# ---------------------------------------------------------------------------
class TestAppearsInSearch:
    def test_appears_in_matter_search(self, client, db_session):
        key = _mk_key("SEARCH")
        body = _build_body(matter_key=key, client_name="Search Client XYZ")
        client.post("/api/matters", json=body)
        db_session.commit()

        resp = client.get(f"/api/matters?q=Search+Client+XYZ")
        assert resp.status_code == status.HTTP_200_OK
        keys = [m["matter_key"] for m in resp.json()["matters"]]
        assert key in keys


# ---------------------------------------------------------------------------
# 12. last_brain_update set when intake narrative provided
# ---------------------------------------------------------------------------
class TestLastBrainUpdate:
    def test_last_brain_update_set_with_intake(self, client, db_session):
        body = _build_body(
            intake_narrative={"update_summary": "Intake narrative"}
        )
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        key = resp.json()["matter_key"]

        db_session.commit()
        m = db_session.get(Matter, key)
        assert m.last_brain_update is not None

    def test_last_brain_update_null_without_intake(self, client, db_session):
        body = _build_body()
        resp = client.post("/api/matters", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        key = resp.json()["matter_key"]

        db_session.commit()
        m = db_session.get(Matter, key)
        assert m.last_brain_update is None
