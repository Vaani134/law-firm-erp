"""
Task Service
============

Business rules and transaction-safe helpers for Task operations.

Transaction rule:
  This service does NOT commit. The caller owns the transaction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.models.matter import Matter
from app.models.task import Task
from app.schemas.task import (
    ActionOwnerType,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
    WaitingOn,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_response(task: Task) -> TaskResponse:
    return TaskResponse(
        task_id=task.task_id,
        matter_key=task.matter_key,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        created_by=task.created_by,
        action_owner_type=task.action_owner_type,
        waiting_on=task.waiting_on,
        waiting_reason=task.waiting_reason,
        waiting_since=task.waiting_since,
        due_at=task.due_at,
        next_action_at=task.next_action_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _apply_status_transition(task: Task, new_status: str) -> None:
    """Mutate waiting/completed timestamps according to business rules."""
    now = datetime.now(timezone.utc)

    if new_status == "WAITING":
        if task.waiting_since is None:
            task.waiting_since = now
    else:
        if task.status == "WAITING" and new_status != "WAITING":
            task.waiting_on = None
            task.waiting_reason = None
            task.waiting_since = None

    if new_status == "COMPLETED":
        task.completed_at = now
    elif task.status == "COMPLETED" and new_status != "COMPLETED":
        task.completed_at = None


def _validate_waiting_fields(status: str, waiting_on: Optional[str]) -> None:
    if status == "WAITING" and not waiting_on:
        raise ValueError("waiting_on is required when status is WAITING.")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def create_task(db: Session, body: TaskCreate) -> TaskResponse:
    matter = db.get(Matter, body.matter_key)
    if matter is None:
        raise ValueError(f"Matter '{body.matter_key}' does not exist.")

    task = Task(
        matter_key=body.matter_key,
        title=body.title.strip(),
        description=body.description,
        task_type=body.task_type,
        status=body.status,
        priority=body.priority,
        assigned_to=body.assigned_to,
        created_by=body.created_by,
        action_owner_type=body.action_owner_type,
        waiting_on=body.waiting_on,
        waiting_reason=body.waiting_reason.strip() if body.waiting_reason else None,
        waiting_since=body.waiting_since,
        due_at=body.due_at,
        next_action_at=body.next_action_at,
    )
    _validate_waiting_fields(task.status, task.waiting_on)
    if task.status == "WAITING" and task.waiting_since is None:
        task.waiting_since = datetime.now(timezone.utc)
    if task.status == "COMPLETED":
        task.completed_at = datetime.now(timezone.utc)

    db.add(task)
    db.flush()
    db.refresh(task)
    return _build_response(task)


def get_task(db: Session, task_id: str) -> Optional[Task]:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        return None
    return db.get(Task, task_uuid)


def update_task(db: Session, task_id: str, body: TaskUpdate) -> TaskResponse:
    task = get_task(db, task_id)
    if task is None:
        raise ValueError("Task not found.")

    updates = body.model_dump(exclude_unset=True)

    if "title" in updates:
        task.title = updates["title"].strip()

    if "description" in updates:
        task.description = updates["description"]

    if "task_type" in updates:
        task.task_type = updates["task_type"]

    if "priority" in updates:
        task.priority = updates["priority"]

    if "assigned_to" in updates:
        task.assigned_to = updates["assigned_to"]

    if "action_owner_type" in updates:
        task.action_owner_type = updates["action_owner_type"]

    if "waiting_on" in updates:
        task.waiting_on = updates["waiting_on"]

    if "waiting_reason" in updates:
        task.waiting_reason = updates["waiting_reason"].strip() if updates["waiting_reason"] else None

    if "waiting_since" in updates:
        task.waiting_since = updates["waiting_since"]

    if "due_at" in updates:
        task.due_at = updates["due_at"]

    if "next_action_at" in updates:
        task.next_action_at = updates["next_action_at"]

    if "status" in updates:
        new_status = updates["status"]
        _validate_waiting_fields(new_status, task.waiting_on)
        _apply_status_transition(task, new_status)
        task.status = new_status

    _validate_waiting_fields(task.status, task.waiting_on)
    if task.status == "WAITING" and task.waiting_since is None:
        task.waiting_since = datetime.now(timezone.utc)

    db.flush()
    db.refresh(task)
    return _build_response(task)


# ---------------------------------------------------------------------------
# Search / List
# ---------------------------------------------------------------------------
def search_tasks(
    db: Session,
    *,
    q: Optional[str] = None,
    matter_key: Optional[str] = None,
    assigned_to: Optional[str] = None,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    action_owner_type: Optional[str] = None,
    waiting_on: Optional[str] = None,
    due_from: Optional[datetime] = None,
    due_to: Optional[datetime] = None,
    next_action_from: Optional[datetime] = None,
    next_action_to: Optional[datetime] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Task], int]:
    base = db.query(Task)

    search_term = (q or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        base = base.filter(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
            )
        )

    if matter_key is not None and matter_key.strip():
        base = base.filter(Task.matter_key == matter_key.strip())

    if assigned_to is not None and assigned_to.strip():
        base = base.filter(Task.assigned_to == uuid.UUID(assigned_to.strip()))

    if task_type is not None and task_type.strip():
        base = base.filter(Task.task_type == task_type.strip())

    if status is not None and status.strip():
        base = base.filter(Task.status == status.strip())

    if priority is not None and priority.strip():
        base = base.filter(Task.priority == priority.strip())

    if action_owner_type is not None and action_owner_type.strip():
        base = base.filter(Task.action_owner_type == action_owner_type.strip())

    if waiting_on is not None and waiting_on.strip():
        base = base.filter(Task.waiting_on == waiting_on.strip())

    if due_from is not None:
        base = base.filter(Task.due_at >= due_from)

    if due_to is not None:
        base = base.filter(Task.due_at <= due_to)

    if next_action_from is not None:
        base = base.filter(Task.next_action_at >= next_action_from)

    if next_action_to is not None:
        base = base.filter(Task.next_action_at <= next_action_to)

    total = base.with_entities(func.count(Task.task_id)).scalar() or 0

    rows = (
        base.order_by(desc(Task.created_at), desc(Task.task_id))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return rows, int(total)
