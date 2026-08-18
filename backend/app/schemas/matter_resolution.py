"""
Pydantic schemas for the Matter Resolution endpoint.

API-layer contracts only — no ORM coupling.
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel


class ResolutionResult(BaseModel):
    """Returned by POST /api/emails/{email_id}/resolve."""

    email_id: uuid.UUID

    # "resolved"         — match found and matter_key written
    # "already_resolved" — matter_key was already populated; no change made
    # "unresolved"       — no matching Matter found; matter_key remains NULL
    status: Literal["resolved", "already_resolved", "unresolved"]

    matter_key: Optional[str]
    match_found: bool
    processing_status: str
