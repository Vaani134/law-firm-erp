"""
POST /api/emails/{email_id}/resolve

Attempts to identify which Matter an already-ingested email belongs to
by matching participant email addresses.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.matter_resolution import ResolutionResult
from app.services.matter_resolver import resolve_matter

router = APIRouter(prefix="/api/emails", tags=["Matter Resolution"])


@router.post(
    "/{email_id}/resolve",
    response_model=ResolutionResult,
    status_code=status.HTTP_200_OK,
    summary="Resolve an email to a Matter",
    description=(
        "Attempts to match the email's sender/recipients against known Matter "
        "participants. Returns the resolution result without modifying Case Brain."
    ),
)
def resolve_email(
    email_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ResolutionResult:
    try:
        return resolve_matter(email_id=email_id, db=db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
