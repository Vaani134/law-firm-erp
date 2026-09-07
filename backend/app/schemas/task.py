"""
Pydantic schemas for the Task endpoints.

POST /api/tasks
GET  /api/tasks
GET  /api/tasks/{task_id}
PATCH /api/tasks/{task_id}
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerated values (mirror DB CHECK constraints)
# ---------------------------------------------------------------------------
TaskType = Literal[
    "LEGAL",
    "CLIENT",
    "DOCUMENT",
    "COMMUNICATION",
    "FOLLOW_UP",
    "FINANCIAL",
    "ADMINISTRATIVE",
    "OTHER",
]

TaskStatus = Literal["OPEN", "IN_PROGRESS", "WAITING", "COMPLETED", "CANCELLED"]

TaskPriority = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]

ActionOwnerType = Literal["INTERNAL", "CLIENT", "EXTERNAL"]

WaitingOn = Literal[
    "CLIENT",
    "OPPOSING_COUNSEL",
    "COURT",
    "GOVERNMENT",
    "PAYMENT",
    "SIGNATURE",
    "DOCUMENT",
    "INTERNAL_APPROVAL",
    "OTHER",
]


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------
class TaskCreate(BaseModel):
    matter_key: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    task_type: TaskType
    status: TaskStatus = "OPEN"
    priority: TaskPriority = "MEDIUM"
    assigned_to: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        description="Creator user UUID. Optional because user authentication is not yet implemented.",
    )
    action_owner_type: ActionOwnerType = "INTERNAL"
    waiting_on: Optional[WaitingOn] = None
    waiting_reason: Optional[str] = Field(default=None, max_length=50)
    waiting_since: Optional[datetime] = None
    due_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def _reject_blank_title(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("title must not be empty or whitespace-only.")
        return value

    @field_validator("waiting_reason")
    @classmethod
    def _reject_blank_waiting_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("waiting_reason must not be empty or whitespace-only.")
        return value


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[uuid.UUID] = None
    action_owner_type: Optional[ActionOwnerType] = None
    waiting_on: Optional[WaitingOn] = None
    waiting_reason: Optional[str] = Field(default=None, max_length=50)
    waiting_since: Optional[datetime] = None
    due_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def _reject_blank_title(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("title must not be empty or whitespace-only.")
        return value

    @field_validator("waiting_reason")
    @classmethod
    def _reject_blank_waiting_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("waiting_reason must not be empty or whitespace-only.")
        return value


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
class TaskResponse(BaseModel):
    task_id: uuid.UUID
    matter_key: str
    title: str
    description: Optional[str]
    task_type: str
    status: str
    priority: str
    assigned_to: Optional[uuid.UUID]
    created_by: Optional[uuid.UUID]
    action_owner_type: str
    waiting_on: Optional[str]
    waiting_reason: Optional[str]
    waiting_since: Optional[datetime]
    due_at: Optional[datetime]
    next_action_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    tasks: List[TaskResponse]
