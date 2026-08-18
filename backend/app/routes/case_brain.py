"""
GET /api/matters/{matter_key}/case-brain

Read-only endpoint that returns the Case Brain timeline for a Matter.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.case_brain_log import CaseBrainLog
from app.models.matter import Matter
from app.schemas.case_brain import CaseBrainLogEntry, CaseBrainTimelineResponse

router = APIRouter(prefix="/api/matters", tags=["Case Brain"])


@router.get(
    "/{matter_key}/case-brain",
    response_model=CaseBrainTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Case Brain timeline for a Matter",
    description=(
        "Returns the Case Brain timeline entries for the specified Matter, "
        "ordered by occurrence time ascending. If the Matter does not exist, "
        "returns 404. If the Matter exists but has no entries, returns an "
        "empty timeline."
    ),
)
def get_case_brain_timeline(
    matter_key: str,
    db: Session = Depends(get_db),
) -> CaseBrainTimelineResponse:
    matter = db.get(Matter, matter_key)
    if matter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Matter '{matter_key}' not found.",
        )

    entries = (
        db.query(CaseBrainLog)
        .filter(CaseBrainLog.matter_key == matter_key)
        .order_by(CaseBrainLog.occurred_at.asc(), CaseBrainLog.brain_entry_id.asc())
        .all()
    )

    return CaseBrainTimelineResponse(
        matter_key=matter_key,
        total=len(entries),
        entries=[
            CaseBrainLogEntry(
                brain_entry_id=entry.brain_entry_id,
                email_id=entry.email_id,
                occurred_at=entry.occurred_at.isoformat(),
                source_type=entry.source_type,
                source_reference=entry.source_reference,
                source_actor=entry.source_actor,
                update_summary=entry.update_summary,
                logged_by=entry.logged_by,
            )
            for entry in entries
        ],
    )
