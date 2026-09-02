"""
POST /api/emails/{email_id}/assign-matter

Manually assign an already-ingested email to a specific Matter.

This is a human-in-the-loop workflow distinct from automatic Matter Resolution.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email import Email
from app.schemas.matter_assignment import MatterAssignmentRequest, MatterAssignmentResponse
from app.services.matter_assignment import assign_matter

router = APIRouter(prefix="/api/emails", tags=["Matter Assignment"])


@router.post(
    "/{email_id}/assign-matter",
    response_model=MatterAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually assign an email to a Matter",
    description=(
        "Explicitly assign an ingested email to a specific Matter. "
        "Returns 409 if the email is already assigned to a different Matter. "
        "Returns 404 if the email or Matter does not exist."
    ),
)
def assign_email_to_matter(
    email_id: uuid.UUID,
    body: MatterAssignmentRequest,
    db: Session = Depends(get_db),
) -> MatterAssignmentResponse:
    try:
        result = assign_matter(email_id=email_id, matter_key=body.matter_key, db=db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if result == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{email_id}' is already assigned to a different Matter.",
        )

    email_row = db.get(Email, email_id)
    db.commit()
    db.refresh(email_row)

    return MatterAssignmentResponse(
        email_id=email_id,
        status=result,
        matter_key=email_row.matter_key,
        processing_status=email_row.processing_status,
    )
