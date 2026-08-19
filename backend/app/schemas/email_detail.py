"""
Pydantic schemas for the Email Detail API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class EmailDetailResponse(BaseModel):
    """Complete stored information for an ingested email."""

    email_id: str
    message_id: Optional[str]
    matter_key: Optional[str]
    sender: str
    to_recipients: Optional[List[dict]]
    cc_recipients: Optional[List[dict]]
    subject: Optional[str]
    body_text: Optional[str]
    received_at: Optional[datetime]
    raw_file_path: str
    content_hash: str
    processing_status: str
    created_at: datetime
    updated_at: datetime
