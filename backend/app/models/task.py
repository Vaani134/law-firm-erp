"""
Task model — represents a work item tied to a legal Matter.

Table: tasks
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.matter import Matter


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="Task UUID primary key",
    )

    matter_key: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("matters.matter_key", ondelete="RESTRICT"),
        nullable=False,
        comment="FK to matters.matter_key",
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Short task title",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed task description",
    )
    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="LEGAL | CLIENT | DOCUMENT | COMMUNICATION | FOLLOW_UP | FINANCIAL | ADMINISTRATIVE | OTHER",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="OPEN",
        comment="OPEN | IN_PROGRESS | WAITING | COMPLETED | CANCELLED",
    )
    priority: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="MEDIUM",
        comment="LOW | MEDIUM | HIGH | URGENT",
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Assigned user UUID. FK cannot be enforced until the users table exists.",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Creator user UUID. Optional because authentication is not yet implemented. A future migration will make this NOT NULL and add a FK to users.user_id.",
    )
    action_owner_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="INTERNAL",
        comment="INTERNAL | CLIENT | EXTERNAL",
    )
    waiting_on: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="CLIENT | OPPOSING_COUNSEL | COURT | GOVERNMENT | PAYMENT | SIGNATURE | DOCUMENT | INTERNAL_APPROVAL | OTHER",
    )
    waiting_reason: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Free-form reason when waiting",
    )
    waiting_since: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the task entered WAITING state",
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the task is expected to be completed",
    )
    next_action_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the firm should take the next action",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the task was marked COMPLETED",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last-modified timestamp",
    )

    matter: Mapped[Optional["Matter"]] = relationship(
        "Matter",
        back_populates="tasks",
    )

    __table_args__ = (
        Index("ix_tasks_matter_key", "matter_key"),
        Index("ix_tasks_assigned_to", "assigned_to"),
        Index("ix_tasks_status", "status"),
        Index(
            "ix_tasks_matter_key_status_due_at",
            "matter_key",
            "status",
            "due_at",
        ),
        Index(
            "ix_tasks_assigned_to_status_due_at",
            "assigned_to",
            "status",
            "due_at",
        ),
        Index(
            "ix_tasks_next_action_at_actionable",
            "next_action_at",
            postgresql_where="status IN ('OPEN', 'IN_PROGRESS', 'WAITING')",
        ),
        Index(
            "ix_tasks_waiting_next_action",
            "waiting_on",
            "waiting_reason",
            "next_action_at",
            postgresql_where="status = 'WAITING'",
        ),
        CheckConstraint(
            "task_type IN ('LEGAL','CLIENT','DOCUMENT','COMMUNICATION','FOLLOW_UP','FINANCIAL','ADMINISTRATIVE','OTHER')",
            name="ck_tasks_task_type",
        ),
        CheckConstraint(
            "status IN ('OPEN','IN_PROGRESS','WAITING','COMPLETED','CANCELLED')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('LOW','MEDIUM','HIGH','URGENT')",
            name="ck_tasks_priority",
        ),
        CheckConstraint(
            "action_owner_type IN ('INTERNAL','CLIENT','EXTERNAL')",
            name="ck_tasks_action_owner_type",
        ),
        CheckConstraint(
            "waiting_on IS NULL OR waiting_on IN ('CLIENT','OPPOSING_COUNSEL','COURT','GOVERNMENT','PAYMENT','SIGNATURE','DOCUMENT','INTERNAL_APPROVAL','OTHER')",
            name="ck_tasks_waiting_on",
        ),
    )

    def __repr__(self) -> str:
        return f"<Task {self.task_id} | {self.title!r} [{self.status}]>"
