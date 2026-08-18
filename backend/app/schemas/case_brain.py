"""
Pydantic schemas for the Case Brain timeline API.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class CaseBrainLogEntry(BaseModel):
    """A single entry in the Case Brain timeline."""

    brain_entry_id: int
    email_id: Optional[uuid.UUID]
    occurred_at: str
    source_type: str
    source_reference: Optional[str]
    source_actor: Optional[str]
    update_summary: str
    logged_by: Optional[str]


class CaseBrainTimelineResponse(BaseModel):
    """Timeline response for a Matter's Case Brain log."""

    matter_key: str
    total: int
    entries: list[CaseBrainLogEntry]
