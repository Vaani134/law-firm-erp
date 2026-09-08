"""
MatterEvent model — structured, append-only event record for matter activity.

Table: matter_events

Design rules:
  - No UPDATE or DELETE should ever be issued against this table.
  - event_type and source_type are application-level validated strings.
  - metadata stores structured JSONB data, not arbitrary prose.
  - Partial unique index prevents duplicate events when source_reference is present.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    func,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.matter import Matter


class MatterEvent(Base):
    __tablename__ = "matter_events"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="Event UUID primary key",
    )

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    matter_key: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("matters.matter_key", ondelete="RESTRICT"),
        nullable=False,
        comment="FK to matters.matter_key",
    )

    # ------------------------------------------------------------------
    # Event classification
    # ------------------------------------------------------------------
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="MATTER_CREATED | EMAIL_RECEIVED | EMAIL_ASSIGNED | CASE_BRAIN_UPDATED",
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="MATTER | EMAIL | CASE_BRAIN",
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional source artefact identifier",
    )

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="When the event actually happened",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this event record was created",
    )

    # ------------------------------------------------------------------
    # Structured payload
    # ------------------------------------------------------------------
    event_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Event-specific structured data",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    matter: Mapped["Matter"] = relationship(
        "Matter",
        back_populates="matter_events",
    )

    # ------------------------------------------------------------------
    # Indexes / constraints
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_matter_events_matter_key", "matter_key"),
        Index("ix_matter_events_event_type", "event_type"),
        Index("ix_matter_events_occurred_at", "occurred_at"),
        Index(
            "ix_matter_events_matter_key_occurred_at",
            "matter_key",
            "occurred_at",
        ),
        CheckConstraint(
            "event_type IN ('MATTER_CREATED','EMAIL_RECEIVED','EMAIL_ASSIGNED','CASE_BRAIN_UPDATED')",
            name="ck_matter_events_event_type",
        ),
        CheckConstraint(
            "source_type IN ('MATTER','EMAIL','CASE_BRAIN')",
            name="ck_matter_events_source_type",
        ),
        Index(
            "uq_matter_events_source_ref",
            "source_type",
            "source_reference",
            "event_type",
            unique=True,
            postgresql_where="source_reference IS NOT NULL",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MatterEvent {self.event_id} "
            f"| {self.event_type} @ {self.matter_key}>"
        )
