"""
GET /api/emails/{email_id}

Read-only endpoint that returns the complete stored information for a specific
ingested email.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email import Email
from app.schemas.email_detail import EmailDetailResponse

router = APIRouter(prefix="/api/emails", tags=["Email Detail"])


@router.get(
    "/{email_id}",
    response_model=EmailDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get email detail",
    description=(
        "Returns the complete stored information for the specified email. "
        "If the email does not exist, returns 404."
    ),
)
def get_email_detail(
    email_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> EmailDetailResponse:
    email_row = db.get(Email, email_id)
    if email_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )

    return EmailDetailResponse(
        email_id=str(email_row.email_id),
        message_id=email_row.message_id,
        matter_key=email_row.matter_key,
        sender=email_row.sender,
        to_recipients=email_row.to_recipients,
        cc_recipients=email_row.cc_recipients,
        subject=email_row.subject,
        body_text=email_row.body_text,
        received_at=email_row.received_at,
        raw_file_path=email_row.raw_file_path,
        content_hash=email_row.content_hash,
        processing_status=email_row.processing_status,
        created_at=email_row.created_at,
        updated_at=email_row.updated_at,
    )
