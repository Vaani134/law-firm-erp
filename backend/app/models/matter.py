"""
Matter model — represents one legal matter / case.

Table: matters
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Index, String, Text, func
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.matter_participant import MatterParticipant
    from app.models.email import Email
    from app.models.case_brain_log import CaseBrainLog


class Matter(Base):
    __tablename__ = "matters"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    matter_key: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Business-level composite key, e.g. ACME-2024-001",
    )

    # ------------------------------------------------------------------
    # Core identity
    # ------------------------------------------------------------------
    client_id: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Client identifier",
    )
    matter_id: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Matter identifier within the client",
    )
    client_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    matter_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    practice_area: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    matter_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    matter_description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    matter_aliases_identifiers: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text aliases and alternative identifiers for fuzzy matching",
    )

    # ------------------------------------------------------------------
    # Status / assignment
    # ------------------------------------------------------------------
    matter_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="open | closed | pending | suspended",
    )
    primary_attorney: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    last_brain_update: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Last time Case Brain was updated for this matter",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    participants: Mapped[List["MatterParticipant"]] = relationship(
        "MatterParticipant",
        back_populates="matter",
        cascade="all, delete-orphan",
    )
    emails: Mapped[List["Email"]] = relationship(
        "Email",
        back_populates="matter",
    )
    brain_log_entries: Mapped[List["CaseBrainLog"]] = relationship(
        "CaseBrainLog",
        back_populates="matter",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # matter_key is the PK — already has a unique B-tree index.
        Index("ix_matters_client_id", "client_id"),
        Index("ix_matters_matter_status", "matter_status"),
    )

    def __repr__(self) -> str:
        return f"<Matter {self.matter_key!r} | {self.matter_name!r}>"
