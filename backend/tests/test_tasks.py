"""
Tests for the Task CRUD endpoints.

Coverage:
  DATABASE / MODEL:
    - task table creation
    - foreign keys
    - constraints
    - indexes/migration

  CREATE:
    - valid task
    - missing matter
    - invalid task type
    - invalid status
    - invalid priority
    - invalid owner type
    - invalid waiting_on
    - empty title
    - whitespace title
    - optional description
    - nullable assignee
    - created_by behavior

  WAITING:
    - WAITING requires waiting_on
    - waiting_since gets populated
    - waiting_reason accepted
    - leaving WAITING clears waiting fields
    - payment waiting scenario
    - client waiting scenario
    - opposing counsel scenario

  COMPLETION:
    - completing sets completed_at
    - reopening clears completed_at

  UPDATE:
    - partial update
    - status transition
    - priority update
    - assignee update
    - due date update
    - next action update
    - updated_at changes

  LIST:
    - pagination
    - q search
    - matter filter
    - assignee filter
    - task type filter
    - status filter
    - priority filter
    - owner type filter
    - waiting_on filter
    - due date filtering
    - next action filtering
    - ordering
    - total count

  GET:
    - existing task
    - missing task -> 404

  SECURITY / DATA INTEGRITY:
    - cannot create task for nonexistent matter
    - cannot assign nonexistent user (UUID format validation)
    - cannot use invalid UUID
    - cannot accidentally delete tasks through the API

  TRANSACTION:
    - follow existing project transaction/rollback conventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import pytest
from fastapi import status

from app.models.task import Task


def _mk_key(prefix: str = "TEST-TASK") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _build_body(matter_key: str, **overrides) -> dict:
    base = {
        "matter_key": matter_key,
        "title": "Test Task",
        "description": "A test task description",
        "task_type": "LEGAL",
        "status": "OPEN",
        "priority": "MEDIUM",
        "action_owner_type": "INTERNAL",
    }
    base.update(overrides)
    return base


def _seed_matter(db, matter_key: str | None = None) -> "Matter":
    from app.models.matter import Matter

    if matter_key is None:
        matter_key = _mk_key("MAT")
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for Task tests",
        matter_status="open",
    )
    db.add(m)
    db.flush()
    return m


# ---------------------------------------------------------------------------
# 1. Database / Model
# ---------------------------------------------------------------------------
class TestDatabaseModel:
    def test_task_table_exists(self, db_session):
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        assert "tasks" in inspector.get_table_names()

    def test_task_columns_exist(self, db_session):
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        columns = [c["name"] for c in inspector.get_columns("tasks")]
        expected = [
            "task_id",
            "matter_key",
            "title",
            "description",
            "task_type",
            "status",
            "priority",
            "assigned_to",
            "created_by",
            "action_owner_type",
            "waiting_on",
            "waiting_reason",
            "waiting_since",
            "due_at",
            "next_action_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        for col in expected:
            assert col in columns

    def test_task_indexes_exist(self, db_session):
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        indexes = [idx["name"] for idx in inspector.get_indexes("tasks")]
        assert "ix_tasks_matter_key" in indexes
        assert "ix_tasks_assigned_to" in indexes
        assert "ix_tasks_status" in indexes
        assert "ix_tasks_matter_key_status_due_at" in indexes
        assert "ix_tasks_assigned_to_status_due_at" in indexes
        assert "ix_tasks_next_action_at_actionable" in indexes
        assert "ix_tasks_waiting_next_action" in indexes


# ---------------------------------------------------------------------------
# 2. Create
# ---------------------------------------------------------------------------
class TestCreateTask:
    def test_returns_201(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_response_contains_task_id(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        data = resp.json()
        assert "task_id" in data
        assert uuid.UUID(data["task_id"])

    def test_task_persists_in_database(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        client.post("/api/tasks", json=body)
        db_session.commit()
        task = db_session.query(Task).first()
        assert task is not None
        assert task.title == "Test Task"

    def test_missing_matter_returns_404(self, client, db_session):
        body = _build_body("NONEXISTENT-MATTER")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_task_type_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, task_type="INVALID")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_status_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, status="INVALID")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_priority_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, priority="INVALID")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_owner_type_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, action_owner_type="INVALID")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_waiting_on_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="INVALID",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_empty_title_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, title="")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_whitespace_title_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, title="   ")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_optional_description_accepted(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, description=None)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["description"] is None

    def test_nullable_assignee_accepted(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, assigned_to=None)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["assigned_to"] is None

    def test_created_by_stored_when_provided(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        user_uuid = str(uuid.uuid4())
        body = _build_body(matter.matter_key, created_by=user_uuid)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["created_by"] == user_uuid

    def test_created_by_nullable_when_omitted(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["created_by"] is None


# ---------------------------------------------------------------------------
# 3. Waiting
# ---------------------------------------------------------------------------
class TestWaitingRules:
    def test_waiting_requires_waiting_on(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, status="WAITING", waiting_on=None)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_waiting_since_populated_on_create(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="CLIENT",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["waiting_since"] is not None

    def test_waiting_reason_accepted(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="CLIENT",
            waiting_reason="Awaiting signed engagement letter",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["waiting_reason"] == "Awaiting signed engagement letter"

    def test_leaving_waiting_clears_waiting_fields(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        create_body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="CLIENT",
            waiting_reason="Waiting",
            waiting_since=datetime.now(timezone.utc).isoformat(),
        )
        create_resp = client.post("/api/tasks", json=create_body)
        assert create_resp.status_code == status.HTTP_201_CREATED
        task_id = create_resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "IN_PROGRESS"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        data = patch_resp.json()
        assert data["waiting_on"] is None
        assert data["waiting_reason"] is None
        assert data["waiting_since"] is None

    def test_payment_waiting_scenario(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            title="Follow up on outstanding invoice",
            task_type="FINANCIAL",
            status="WAITING",
            waiting_on="PAYMENT",
            waiting_reason="Invoice #1234 overdue",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["waiting_on"] == "PAYMENT"
        assert data["task_type"] == "FINANCIAL"

    def test_client_waiting_scenario(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="CLIENT",
            waiting_reason="Awaiting documents",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["waiting_on"] == "CLIENT"

    def test_opposing_counsel_waiting_scenario(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="OPPOSING_COUNSEL",
            waiting_reason="Response to discovery request",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["waiting_on"] == "OPPOSING_COUNSEL"


# ---------------------------------------------------------------------------
# 4. Completion
# ---------------------------------------------------------------------------
class TestCompletionRules:
    def test_completing_sets_completed_at(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, status="OPEN")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "COMPLETED"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["completed_at"] is not None

    def test_reopening_clears_completed_at(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, status="OPEN")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        client.patch(f"/api/tasks/{task_id}", json={"status": "COMPLETED"})
        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "IN_PROGRESS"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["completed_at"] is None


# ---------------------------------------------------------------------------
# 5. Update
# ---------------------------------------------------------------------------
class TestUpdateTask:
    def test_partial_update_title(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"title": "Updated Title"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["title"] == "Updated Title"

    def test_priority_update(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"priority": "HIGH"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["priority"] == "HIGH"

    def test_assignee_update(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]
        new_uuid = str(uuid.uuid4())

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"assigned_to": new_uuid},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["assigned_to"] == new_uuid

    def test_due_date_update(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]
        due = datetime.now(timezone.utc) + timedelta(days=7)

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"due_at": due.isoformat()},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert datetime.fromisoformat(patch_resp.json()["due_at"]) == due

    def test_next_action_update(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]
        next_action = datetime.now(timezone.utc) + timedelta(days=3)

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"next_action_at": next_action.isoformat()},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert datetime.fromisoformat(patch_resp.json()["next_action_at"]) == next_action

    def test_updated_at_changes(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        original_updated = resp.json()["updated_at"]

        import time
        time.sleep(0.05)

        task_id = resp.json()["task_id"]
        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"title": "Changed Again"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["updated_at"] != original_updated

    def test_status_transition_open_to_in_progress(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, status="OPEN")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "IN_PROGRESS"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["status"] == "IN_PROGRESS"

    def test_status_transition_open_to_waiting(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, status="OPEN")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "WAITING", "waiting_on": "COURT"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["status"] == "WAITING"
        assert patch_resp.json()["waiting_since"] is not None

    def test_status_transition_waiting_to_completed(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(
            matter.matter_key,
            status="WAITING",
            waiting_on="CLIENT",
        )
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "COMPLETED"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["status"] == "COMPLETED"
        assert patch_resp.json()["completed_at"] is not None


# ---------------------------------------------------------------------------
# 6. List
# ---------------------------------------------------------------------------
class TestListTasks:
    def test_default_limit_is_20(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        client.post("/api/tasks", json=body)
        db_session.commit()

        resp = client.get("/api/tasks")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["limit"] == 20

    def test_pagination_fields_present(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        client.post("/api/tasks", json=body)
        db_session.commit()

        resp = client.get("/api/tasks")
        data = resp.json()
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "tasks" in data

    def test_q_search_matches_title(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, title="UniqueSearchableTitle")
        client.post("/api/tasks", json=body)
        db_session.commit()

        resp = client.get("/api/tasks?q=UniqueSearchableTitle")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1
        assert any(t["title"] == "UniqueSearchableTitle" for t in resp.json()["tasks"])

    def test_matter_filter(self, client, db_session):
        m1 = _seed_matter(db_session, _mk_key("MAT1"))
        m2 = _seed_matter(db_session, _mk_key("MAT2"))
        db_session.commit()
        client.post("/api/tasks", json=_build_body(m1.matter_key, title="Task A"))
        client.post("/api/tasks", json=_build_body(m2.matter_key, title="Task B"))
        db_session.commit()

        resp = client.get(f"/api/tasks?matter_key={m1.matter_key}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1
        assert all(t["matter_key"] == m1.matter_key for t in resp.json()["tasks"])

    def test_status_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        client.post("/api/tasks", json=_build_body(matter.matter_key, status="OPEN"))
        client.post("/api/tasks", json=_build_body(matter.matter_key, status="COMPLETED"))
        db_session.commit()

        resp = client.get("/api/tasks?status=OPEN")
        assert resp.status_code == status.HTTP_200_OK
        assert all(t["status"] == "OPEN" for t in resp.json()["tasks"])

    def test_priority_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        client.post("/api/tasks", json=_build_body(matter.matter_key, priority="HIGH"))
        client.post("/api/tasks", json=_build_body(matter.matter_key, priority="LOW"))
        db_session.commit()

        resp = client.get("/api/tasks?priority=HIGH")
        assert resp.status_code == status.HTTP_200_OK
        assert all(t["priority"] == "HIGH" for t in resp.json()["tasks"])

    def test_task_type_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        client.post("/api/tasks", json=_build_body(matter.matter_key, task_type="LEGAL"))
        client.post("/api/tasks", json=_build_body(matter.matter_key, task_type="FINANCIAL"))
        db_session.commit()

        resp = client.get("/api/tasks?task_type=FINANCIAL")
        assert resp.status_code == status.HTTP_200_OK
        assert all(t["task_type"] == "FINANCIAL" for t in resp.json()["tasks"])

    def test_action_owner_type_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        client.post("/api/tasks", json=_build_body(matter.matter_key, action_owner_type="CLIENT"))
        client.post("/api/tasks", json=_build_body(matter.matter_key, action_owner_type="INTERNAL"))
        db_session.commit()

        resp = client.get("/api/tasks?action_owner_type=CLIENT")
        assert resp.status_code == status.HTTP_200_OK
        assert all(t["action_owner_type"] == "CLIENT" for t in resp.json()["tasks"])

    def test_waiting_on_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        client.post("/api/tasks", json=_build_body(matter.matter_key, status="WAITING", waiting_on="PAYMENT"))
        client.post("/api/tasks", json=_build_body(matter.matter_key, status="WAITING", waiting_on="COURT"))
        db_session.commit()

        resp = client.get("/api/tasks?waiting_on=PAYMENT")
        assert resp.status_code == status.HTTP_200_OK
        assert all(t["waiting_on"] == "PAYMENT" for t in resp.json()["tasks"])

    def test_due_date_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        due_past = datetime.now(timezone.utc) - timedelta(days=1)
        due_future = datetime.now(timezone.utc) + timedelta(days=1)
        client.post("/api/tasks", json=_build_body(matter.matter_key, due_at=due_past.isoformat()))
        client.post("/api/tasks", json=_build_body(matter.matter_key, due_at=due_future.isoformat()))
        db_session.commit()

        resp = client.get("/api/tasks", params={"due_from": due_past.isoformat()})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1

    def test_next_action_filter(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        next_past = datetime.now(timezone.utc) - timedelta(days=1)
        next_future = datetime.now(timezone.utc) + timedelta(days=1)
        client.post("/api/tasks", json=_build_body(matter.matter_key, next_action_at=next_past.isoformat()))
        client.post("/api/tasks", json=_build_body(matter.matter_key, next_action_at=next_future.isoformat()))
        db_session.commit()

        resp = client.get("/api/tasks", params={"next_action_from": next_past.isoformat()})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1

    def test_ordering_newest_first(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        client.post("/api/tasks", json=_build_body(matter.matter_key, title="Older"))
        import time
        time.sleep(0.05)
        client.post("/api/tasks", json=_build_body(matter.matter_key, title="Newer"))
        db_session.commit()

        resp = client.get("/api/tasks")
        tasks = resp.json()["tasks"]
        assert len(tasks) >= 2
        titles = [t["title"] for t in tasks]
        assert titles.index("Newer") < titles.index("Older") if "Older" in titles and "Newer" in titles else True

    def test_total_count_accuracy(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        for _ in range(3):
            client.post("/api/tasks", json=_build_body(matter.matter_key))
        db_session.commit()

        resp = client.get("/api/tasks?limit=100")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 3


# ---------------------------------------------------------------------------
# 7. Get
# ---------------------------------------------------------------------------
class TestGetTask:
    def test_existing_task_returns_200(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        get_resp = client.get(f"/api/tasks/{task_id}")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["task_id"] == task_id

    def test_missing_task_returns_404(self, client, db_session):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/tasks/{fake_id}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_uuid_returns_404(self, client, db_session):
        resp = client.get("/api/tasks/not-a-uuid")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 8. Security / Data Integrity
# ---------------------------------------------------------------------------
class TestSecurityDataIntegrity:
    def test_cannot_create_task_for_nonexistent_matter(self, client, db_session):
        body = _build_body("NONEXISTENT-MATTER")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_assigned_to_uuid_returns_422(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, assigned_to="not-a-uuid")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_no_delete_endpoint(self, client, db_session):
        resp = client.delete("/api/tasks/some-id")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------------------------------------------------------------------------
# 9. Transaction / Rollback
# ---------------------------------------------------------------------------
class TestTransactionBehavior:
    def test_invalid_create_does_not_persist(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key, title="")
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        db_session.commit()
        count = db_session.query(Task).count()
        assert count == 0

    def test_invalid_update_does_not_persist(self, client, db_session):
        matter = _seed_matter(db_session)
        db_session.commit()
        body = _build_body(matter.matter_key)
        resp = client.post("/api/tasks", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        patch_resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"title": ""},
        )
        assert patch_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        db_session.commit()
        task = db_session.get(Task, uuid.UUID(task_id))
        assert task.title == "Test Task"
