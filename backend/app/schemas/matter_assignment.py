"""
Pydantic schemas for the Matter Assignment endpoint.
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel


class MatterAssignmentRequest(BaseModel):
    """Request body for manually assigning an email to a Matter."""

    matter_key: str


class MatterAssignmentResponse(BaseModel):
    """Response returned by POST /api/emails/{email_id}/assign-matter."""

    email_id: uuid.UUID
    status: Literal["assigned", "already_assigned"]
    matter_key: Optional[str]
    processing_status: str
