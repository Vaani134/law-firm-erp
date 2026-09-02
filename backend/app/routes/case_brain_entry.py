"""
POST /api/matters/{matter_key}/case-brain

Manually author a Case Brain entry for an existing Matter.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.case_brain_entry import (
    CaseBrainEntryCreate,
    CaseBrainEntryResponse,
)
from app.services.case_brain import create_manual_case_brain_log

router = APIRouter(prefix="/api/matters", tags=["Case Brain"])


@router.post(
    "/{matter_key}/case-brain",
    response_model=CaseBrainEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually author a Case Brain entry",
    description=(
        "Append a manually authored CaseBrainLog entry to a Matter. "
        "The email ingestion path is the only writer of source_type='email' "
        "rows; this endpoint accepts 'manual', 'intake', 'system', or 'import'. "
        "Returns 404 if the Matter does not exist."
    ),
)
def create_case_brain_entry(
    matter_key: str,
    body: CaseBrainEntryCreate,
    db: Session = Depends(get_db),
) -> CaseBrainEntryResponse:
    try:
        log_entry = create_manual_case_brain_log(
            db,
            matter_key,
            source_type=body.source_type,
            update_summary=body.update_summary,
            source_reference=body.source_reference,
            source_actor=body.source_actor,
            occurred_at=body.occurred_at,
            logged_by=body.logged_by,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if "not found" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from exc

    db.refresh(log_entry)

    return CaseBrainEntryResponse(
        brain_entry_id=log_entry.brain_entry_id,
        matter_key=log_entry.matter_key,
        email_id=log_entry.email_id,
        occurred_at=log_entry.occurred_at,
        logged_at=log_entry.logged_at,
        source_type=log_entry.source_type,
        source_reference=log_entry.source_reference,
        source_actor=log_entry.source_actor,
        update_summary=log_entry.update_summary,
        logged_by=log_entry.logged_by,
    )
