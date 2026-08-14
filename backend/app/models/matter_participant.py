"""
MatterParticipant model — people/organisations linked to a matter.

Table: matter_participants
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.matter import Matter


class MatterParticipant(Base):
    __tablename__ = "matter_participants"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    participant_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Surrogate auto-increment PK",
    )

    # ------------------------------------------------------------------
    # Foreign key to matters
    # ------------------------------------------------------------------
    matter_key: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("matters.matter_key", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Participant details
    # ------------------------------------------------------------------
    participant_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    email_address: Mapped[Optional[str]] = mapped_column(
        String(320),
        nullable=True,
    )
    organization: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    role_relationship: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. client, opposing_counsel, expert_witness",
    )

    # ------------------------------------------------------------------
    # Active flag
    # ------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # ------------------------------------------------------------------
    # Relationship (N→1 Matter)
    # ------------------------------------------------------------------
    matter: Mapped["Matter"] = relationship(
        "Matter",
        back_populates="participants",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_matter_participants_matter_key", "matter_key"),
        Index("ix_matter_participants_email_address", "email_address"),
    )

    def __repr__(self) -> str:
        return (
            f"<MatterParticipant {self.participant_id} "
            f"| {self.participant_name!r} [{self.matter_key}]>"
        )
