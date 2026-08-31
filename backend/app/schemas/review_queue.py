"""
Pydantic schemas for the Review Queue API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ReviewQueueEmailResponse(BaseModel):
    """Email information for the Review Queue."""

    email_id: str
    message_id: Optional[str]
    sender: str
    to_recipients: Optional[List[dict]]
    cc_recipients: Optional[List[dict]]
    subject: Optional[str]
    received_at: Optional[datetime]
    processing_status: str
    matter_key: Optional[str]


class ReviewQueueResponse(BaseModel):
    """Response containing all emails requiring manual review."""

    total: int
    emails: List[ReviewQueueEmailResponse]
