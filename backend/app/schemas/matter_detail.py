"""
Pydantic schemas for the Matter Detail API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class MatterResponse(BaseModel):
    """Matter information for Matter Detail."""

    matter_key: str
    client_id: str
    matter_id: str
    client_name: str
    matter_name: str
    practice_area: Optional[str]
    matter_type: Optional[str]
    matter_description: str
    matter_aliases_identifiers: Optional[str]
    matter_status: str
    primary_attorney: Optional[str]
    last_brain_update: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class MatterParticipantResponse(BaseModel):
    """Participant information for Matter Detail."""

    participant_id: int
    matter_key: str
    participant_name: str
    email_address: Optional[str]
    organization: Optional[str]
    role_relationship: Optional[str]
    is_active: bool


class MatterEmailResponse(BaseModel):
    """Email information for Matter Detail."""

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


class MatterCaseBrainEntry(BaseModel):
    """Case Brain log entry for Matter Detail."""

    brain_entry_id: int
    email_id: Optional[uuid.UUID]
    occurred_at: datetime
    source_type: str
    source_reference: Optional[str]
    source_actor: Optional[str]
    update_summary: str
    logged_by: Optional[str]


class MatterDetailResponse(BaseModel):
    """Complete Matter detail with participants, emails, and case brain timeline."""

    matter: MatterResponse
    participants: List[MatterParticipantResponse]
    emails: List[MatterEmailResponse]
    case_brain: List[MatterCaseBrainEntry]
