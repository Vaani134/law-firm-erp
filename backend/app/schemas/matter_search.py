"""
Pydantic schemas for the Matter Search endpoint.

GET /api/matters — collection-level, read-only.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class MatterSummary(BaseModel):
    """Lightweight Matter summary used for search results."""

    matter_key: str
    client_name: str
    matter_name: str
    practice_area: Optional[str]
    matter_type: Optional[str]
    matter_status: str
    primary_attorney: Optional[str]


class MatterSearchResponse(BaseModel):
    """Paginated response for GET /api/matters."""

    total: int
    limit: int
    offset: int
    matters: List[MatterSummary]
