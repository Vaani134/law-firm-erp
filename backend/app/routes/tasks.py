"""
Task CRUD endpoints.

POST   /api/tasks
GET    /api/tasks
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.task import (
    create_task,
    get_task,
    search_tasks,
    update_task,
)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Task",
    description=(
        "Create a new Task linked to an existing Matter. "
        "Optional filters and timestamps allow full task specification. "
        "created_by is optional because user authentication is not yet implemented."
    ),
)
def create_task_endpoint(
    body: TaskCreate,
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        result = create_task(db, body)
        db.commit()
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if "does not exist" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from exc
    except Exception:
        db.rollback()
        raise

    return result


@router.get(
    "",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search Tasks",
    description=(
        "Returns a paginated list of Tasks. Supports filters for matter, "
        "assignee, task type, status, priority, owner type, waiting state, "
        "and date ranges. Free-text query searches title and description."
    ),
)
def list_tasks(
    q: Optional[str] = Query(
        None,
        description="Free-text search across title and description",
    ),
    matter_key: Optional[str] = Query(
        None,
        description="Filter by matter_key",
    ),
    assigned_to: Optional[str] = Query(
        None,
        description="Filter by assigned_to UUID",
    ),
    task_type: Optional[str] = Query(
        None,
        description="Filter by task_type",
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by status",
    ),
    priority: Optional[str] = Query(
        None,
        description="Filter by priority",
    ),
    action_owner_type: Optional[str] = Query(
        None,
        description="Filter by action_owner_type",
    ),
    waiting_on: Optional[str] = Query(
        None,
        description="Filter by waiting_on",
    ),
    due_from: Optional[datetime] = Query(
        None,
        description="Filter tasks with due_at >= this ISO-8601 datetime",
    ),
    due_to: Optional[datetime] = Query(
        None,
        description="Filter tasks with due_at <= this ISO-8601 datetime",
    ),
    next_action_from: Optional[datetime] = Query(
        None,
        description="Filter tasks with next_action_at >= this ISO-8601 datetime",
    ),
    next_action_to: Optional[datetime] = Query(
        None,
        description="Filter tasks with next_action_at <= this ISO-8601 datetime",
    ),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    rows, total = search_tasks(
        db,
        q=q,
        matter_key=matter_key,
        assigned_to=assigned_to,
        task_type=task_type,
        status=status,
        priority=priority,
        action_owner_type=action_owner_type,
        waiting_on=waiting_on,
        due_from=due_from,
        due_to=due_to,
        next_action_from=next_action_from,
        next_action_to=next_action_to,
        limit=limit,
        offset=offset,
    )
    return TaskListResponse(
        total=total,
        limit=limit,
        offset=offset,
        tasks=[_build_task_response(t) for t in rows],
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a Task by ID",
    description="Returns a single Task by its UUID. 404 if not found.",
)
def get_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
) -> TaskResponse:
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return _build_task_response(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a Task",
    description=(
        "Partially update a Task. Supports status transitions with automatic "
        "timestamp management for WAITING and COMPLETED states."
    ),
)
def update_task_endpoint(
    task_id: str,
    body: TaskUpdate,
    db: Session = Depends(get_db),
) -> TaskResponse:
    try:
        result = update_task(db, task_id, body)
        db.commit()
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from exc
    except Exception:
        db.rollback()
        raise

    return result


def _build_task_response(task: Task) -> TaskResponse:
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
