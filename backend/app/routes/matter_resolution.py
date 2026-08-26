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
from app.models.email import Email
from app.schemas.matter_resolution import ResolutionResult
from app.services.case_brain import create_case_brain_log
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
        result = resolve_matter(email_id=email_id, db=db)
        if result.status == "resolved":
            email_row = db.get(Email, email_id)
            create_case_brain_log(db, email_row, result.matter_key)
            db.commit()
            db.refresh(email_row)
        elif result.status == "unresolved":
            db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
