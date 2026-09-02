"""
GET /api/matters

Collection-level, read-only Matter search/list endpoint.

Returns paginated MatterSummary objects suitable for a reviewer-facing
search UI. Does not modify any records.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import asc, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.matter import Matter
from app.schemas.matter_search import MatterSearchResponse, MatterSummary

router = APIRouter(prefix="/api/matters", tags=["Matter Search"])


@router.get(
    "",
    response_model=MatterSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search and list Matters",
    description=(
        "Returns a paginated list of Matters. Optional free-text query (q) "
        "matches against matter_key, client_name, and matter_name. Optional "
        "filters: status (matter_status) and practice_area. Read-only."
    ),
)
def search_matters(
    q: Optional[str] = Query(
        None,
        description="Free-text search across matter_key, client_name, matter_name",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by matter_status (e.g. open, closed, pending, suspended)",
    ),
    practice_area: Optional[str] = Query(
        None,
        description="Filter by practice_area",
    ),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> MatterSearchResponse:
    base = db.query(Matter)

    search_term = (q or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        base = base.filter(
            or_(
                Matter.matter_key.ilike(pattern),
                Matter.client_name.ilike(pattern),
                Matter.matter_name.ilike(pattern),
            )
        )

    if status_filter is not None and status_filter != "":
        base = base.filter(Matter.matter_status == status_filter)

    if practice_area is not None and practice_area != "":
        base = base.filter(Matter.practice_area == practice_area)

    total = base.with_entities(func.count(Matter.matter_key)).scalar() or 0

    rows = (
        base.order_by(asc(Matter.matter_key))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return MatterSearchResponse(
        total=int(total),
        limit=limit,
        offset=offset,
        matters=[
            MatterSummary(
                matter_key=m.matter_key,
                client_name=m.client_name,
                matter_name=m.matter_name,
                practice_area=m.practice_area,
                matter_type=m.matter_type,
                matter_status=m.matter_status,
                primary_attorney=m.primary_attorney,
            )
            for m in rows
        ],
    )
