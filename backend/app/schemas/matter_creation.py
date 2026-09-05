"""
Pydantic schemas for the Matter Creation (Intake) endpoint.

POST /api/matters
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------
class MatterParticipantCreate(BaseModel):
    """Initial participant for a newly created Matter."""

    participant_name: str = Field(..., min_length=1)
    email_address: Optional[str] = None
    organization: Optional[str] = None
    role_relationship: Optional[str] = None
    is_active: bool = True


# ---------------------------------------------------------------------------
# Intake narrative (optional opening Case Brain entry)
# ---------------------------------------------------------------------------
class IntakeNarrative(BaseModel):
    """Optional intake narrative written as the first Case Brain entry."""

    update_summary: str = Field(..., min_length=1)
    source_actor: Optional[str] = None
    source_reference: Optional[str] = None
    occurred_at: Optional[datetime] = None
    logged_by: Optional[str] = None

    @field_validator("update_summary")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("update_summary must not be empty or whitespace-only.")
        return value


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------
class MatterCreateRequest(BaseModel):
    """Request body for POST /api/matters."""

    matter_key: str = Field(..., min_length=1, max_length=50)
    client_id: str = Field(..., min_length=1, max_length=30)
    matter_id: str = Field(..., min_length=1, max_length=30)
    client_name: str = Field(..., min_length=1, max_length=200)
    matter_name: str = Field(..., min_length=1, max_length=200)
    matter_description: str = Field(..., min_length=1, max_length=500)
    matter_status: str = Field(default="open", pattern=r"^(open|closed|pending|suspended)$")
    practice_area: Optional[str] = Field(default=None, max_length=100)
    matter_type: Optional[str] = Field(default=None, max_length=100)
    matter_aliases_identifiers: Optional[str] = None
    primary_attorney: Optional[str] = Field(default=None, max_length=200)
    participants: Optional[List[MatterParticipantCreate]] = None
    intake_narrative: Optional[IntakeNarrative] = None


# ---------------------------------------------------------------------------
# Response (mirrors MatterResponse + nested collections)
# ---------------------------------------------------------------------------
class MatterParticipantSummary(BaseModel):
    participant_id: int
    matter_key: str
    participant_name: str
    email_address: Optional[str]
    organization: Optional[str]
    role_relationship: Optional[str]
    is_active: bool


class MatterCaseBrainSummary(BaseModel):
    brain_entry_id: int
    email_id: Optional[str]
    occurred_at: datetime
    source_type: str
    source_reference: Optional[str]
    source_actor: Optional[str]
    update_summary: str
    logged_by: Optional[str]


class MatterCreateResponse(BaseModel):
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
    participants: List[MatterParticipantSummary] = []
    case_brain_entries: List[MatterCaseBrainSummary] = []
