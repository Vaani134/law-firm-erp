"""
Pydantic schemas for the Email Ingestion endpoint.

These are the API-layer contracts only — no ORM coupling.
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel


class IngestionSuccess(BaseModel):
    """Returned when a new email is ingested for the first time."""

    status: Literal["ingested"] = "ingested"
    email_id: uuid.UUID
    message_id: Optional[str]
    processing_status: str


class IngestionDuplicate(BaseModel):
    """Returned when the email already exists in the database."""

    status: Literal["duplicate"] = "duplicate"
    email_id: uuid.UUID
    message_id: Optional[str]
    processing_status: str
    duplicate_reason: str  # "message_id" | "content_hash"


# Union type used by the route response annotation
IngestionResponse = IngestionSuccess | IngestionDuplicate
