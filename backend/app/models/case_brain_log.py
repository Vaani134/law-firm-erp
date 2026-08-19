"""
CaseBrainLog model — append-only audit trail of Case Brain updates.

Table: case_brain_log

Design rules:
  - No UPDATE or DELETE should ever be issued against this table.
  - No database UNIQUE constraint exists on email_id.
  - Application-level idempotency currently prevents duplicate
    resolution logs for the same email.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text, func, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.matter import Matter
    from app.models.email import Email


class CaseBrainLog(Base):
    __tablename__ = "case_brain_log"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    brain_entry_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    matter_key: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("matters.matter_key", ondelete="RESTRICT"),
        nullable=False,
        comment="The matter this log entry describes",
    )
    # Nullable — log entries may originate from non-email sources.
    # No UNIQUE constraint: same email can generate multiple entries.
    email_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.email_id", ondelete="SET NULL"),
        nullable=True,
        comment="Source email, if any. Not unique — reprocessing allowed.",
    )

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="When the event being logged actually occurred",
    )
    logged_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this record was written",
    )

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------
    source_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="email | manual | system | import",
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Identifier of the source artefact, e.g. email Message-ID",
    )
    source_actor: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Person or system that triggered this update",
    )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    update_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human/AI-generated narrative of what changed",
    )
    logged_by: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="System component or user that wrote this entry",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    matter: Mapped["Matter"] = relationship(
        "Matter",
        back_populates="brain_log_entries",
    )
    email: Mapped[Optional["Email"]] = relationship(
        "Email",
        back_populates="brain_log_entries",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_case_brain_log_matter_key", "matter_key"),
        Index("ix_case_brain_log_email_id", "email_id"),
        Index("ix_case_brain_log_occurred_at", "occurred_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<CaseBrainLog {self.brain_entry_id} "
            f"| {self.matter_key} @ {self.occurred_at}>"
        )
