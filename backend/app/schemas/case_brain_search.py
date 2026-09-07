"""
Pydantic schemas for the firm-wide Case Brain search endpoint.

GET /api/case-brain
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class CaseBrainSearchEntry(BaseModel):
    """A single Case Brain entry in the firm-wide search response."""

    brain_entry_id: int
    matter_key: str
    email_id: Optional[str] = None
    occurred_at: str
    logged_at: str
    source_type: str
    source_reference: Optional[str] = None
    source_actor: Optional[str] = None
    update_summary: str
    logged_by: Optional[str] = None


class CaseBrainSearchResponse(BaseModel):
    """Paginated firm-wide Case Brain timeline."""

    total: int
    limit: int
    offset: int
    entries: List[CaseBrainSearchEntry]
