"""
POST /api/matters

Create a new Matter with optional initial participants and an optional
opening intake narrative (Case Brain entry).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.matter_creation import MatterCreateRequest, MatterCreateResponse
from app.services.matter_creation import create_matter

router = APIRouter(prefix="/api/matters", tags=["Matter Creation"])


@router.post(
    "",
    response_model=MatterCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Matter",
    description=(
        "Create a new Matter. The caller supplies the matter_key and other "
        "core fields. Optionally include initial participants and an opening "
        "intake narrative (written as a Case Brain entry with source_type='intake'). "
        "Matter creation, participant creation, and optional Case Brain entry "
        "are atomic — any failure rolls back everything."
    ),
)
def create_matter_endpoint(
    body: MatterCreateRequest,
    db: Session = Depends(get_db),
) -> MatterCreateResponse:
    try:
        result = create_matter(db, body)
        db.commit()
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from exc
    except Exception:
        db.rollback()
        raise

    return result
