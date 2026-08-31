"""
GET /api/emails/review-required

Read-only endpoint that returns all emails requiring manual matter review.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email import Email
from app.schemas.review_queue import ReviewQueueEmailResponse, ReviewQueueResponse

router = APIRouter(prefix="/api/emails", tags=["Review Queue"])


@router.get(
    "/review-required",
    response_model=ReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get emails requiring manual review",
    description=(
        "Returns all emails with processing_status = REVIEW_REQUIRED, "
        "ordered by created_at descending."
    ),
)
def get_review_required_emails(
    db: Session = Depends(get_db),
) -> ReviewQueueResponse:
    emails = (
        db.query(Email)
        .filter(Email.processing_status == "REVIEW_REQUIRED")
        .order_by(desc(Email.created_at))
        .all()
    )

    return ReviewQueueResponse(
        total=len(emails),
        emails=[
            ReviewQueueEmailResponse(
                email_id=str(email.email_id),
                message_id=email.message_id,
                sender=email.sender,
                to_recipients=email.to_recipients,
                cc_recipients=email.cc_recipients,
                subject=email.subject,
                received_at=email.received_at,
                processing_status=email.processing_status,
                matter_key=email.matter_key,
            )
            for email in emails
        ],
    )
