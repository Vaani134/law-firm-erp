"""
GET /api/case-brain

Firm-wide, paginated Case Brain timeline across all Matters.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.case_brain_log import CaseBrainLog
from app.schemas.case_brain_search import CaseBrainSearchEntry, CaseBrainSearchResponse

router = APIRouter(prefix="/api", tags=["Case Brain Search"])


@router.get(
    "/case-brain",
    response_model=CaseBrainSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Firm-wide Case Brain timeline",
    description=(
        "Returns a paginated, firm-wide Case Brain timeline across all Matters. "
        "Optional filters: free-text query (q), source_type, matter_key, date range. "
        "Results are ordered newest-first."
    ),
)
def search_case_brain(
    q: Optional[str] = Query(
        None,
        description="Free-text search across update_summary, source_reference, source_actor, matter_key",
    ),
    source_type: Optional[str] = Query(
        None,
        description="Filter by source_type (email, manual, intake, system, import)",
    ),
    matter_key: Optional[str] = Query(
        None,
        description="Exact matter key filter",
    ),
    date_from: Optional[datetime] = Query(
        None,
        description="Filter entries with occurred_at >= this ISO-8601 datetime",
    ),
    date_to: Optional[datetime] = Query(
        None,
        description="Filter entries with occurred_at <= this ISO-8601 datetime",
    ),
    limit: int = Query(50, ge=1, le=200, description="Page size (1-200)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> CaseBrainSearchResponse:
    base = db.query(CaseBrainLog)

    # Free-text search
    search_term = (q or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        base = base.filter(
            or_(
                CaseBrainLog.update_summary.ilike(pattern),
                CaseBrainLog.source_reference.ilike(pattern),
                CaseBrainLog.source_actor.ilike(pattern),
                CaseBrainLog.matter_key.ilike(pattern),
            )
        )

    # Source type filter (case-insensitive)
    if source_type is not None and source_type.strip():
        base = base.filter(
            func.lower(CaseBrainLog.source_type) == source_type.strip().lower()
        )

    # Matter key filter (case-insensitive to match existing conventions)
    if matter_key is not None and matter_key.strip():
        base = base.filter(
            func.lower(CaseBrainLog.matter_key) == matter_key.strip().lower()
        )

    # Date range filters on occurred_at
    if date_from is not None:
        base = base.filter(CaseBrainLog.occurred_at >= date_from)
    if date_to is not None:
        base = base.filter(CaseBrainLog.occurred_at <= date_to)

    total = base.with_entities(func.count(CaseBrainLog.brain_entry_id)).scalar() or 0

    rows = (
        base.order_by(desc(CaseBrainLog.occurred_at), desc(CaseBrainLog.brain_entry_id))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return CaseBrainSearchResponse(
        total=int(total),
        limit=limit,
        offset=offset,
        entries=[
            CaseBrainSearchEntry(
                brain_entry_id=entry.brain_entry_id,
                matter_key=entry.matter_key,
                email_id=str(entry.email_id) if entry.email_id is not None else None,
                occurred_at=entry.occurred_at.isoformat(),
                logged_at=entry.logged_at.isoformat(),
                source_type=entry.source_type,
                source_reference=entry.source_reference,
                source_actor=entry.source_actor,
                update_summary=entry.update_summary,
                logged_by=entry.logged_by,
            )
            for entry in rows
        ],
    )
