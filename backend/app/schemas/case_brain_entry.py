"""
Pydantic schemas for manually authored Case Brain entries.

The existing GET /api/matters/{matter_key}/case-brain timeline endpoint
returns the read-side CaseBrainLogEntry. This module adds the write-side
schemas for entries that are not produced by the email ingestion path.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# Source types accepted by the manual entry endpoint.
# "email" is intentionally excluded: email-source entries are written
# only by the ingestion path.
ManualSourceType = Literal["manual", "intake", "system", "import"]


class CaseBrainEntryCreate(BaseModel):
    """Request body for POST /api/matters/{matter_key}/case-brain."""

    source_type: ManualSourceType
    source_reference: Optional[str] = None
    source_actor: Optional[str] = None
    update_summary: str = Field(..., min_length=1)
    occurred_at: Optional[datetime] = None
    logged_by: Optional[str] = None

    @field_validator("update_summary")
    @classmethod
    def _reject_blank_summary(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("update_summary must not be empty or whitespace-only.")
        return value


class CaseBrainEntryResponse(BaseModel):
    """Response returned by POST /api/matters/{matter_key}/case-brain."""

    brain_entry_id: int
    matter_key: str
    email_id: Optional[uuid.UUID]
    occurred_at: datetime
    logged_at: datetime
    source_type: str
    source_reference: Optional[str]
    source_actor: Optional[str]
    update_summary: str
    logged_by: Optional[str]
