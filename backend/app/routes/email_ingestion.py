"""
POST /api/emails/ingest

Accepts an uploaded .eml file and delegates to the ingestion service.
Returns IngestionSuccess (201) or IngestionDuplicate (200).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.email_ingestion import IngestionDuplicate, IngestionSuccess
from app.services.email_ingestion import ingest_eml

router = APIRouter(prefix="/api/emails", tags=["Email Ingestion"])

# Maximum upload size: 25 MB (generous for a single .eml with attachments)
MAX_EML_SIZE_BYTES = 25 * 1024 * 1024


@router.post(
    "/ingest",
    response_model=IngestionSuccess | IngestionDuplicate,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a .eml file",
    description=(
        "Upload a raw RFC 2822 .eml file. "
        "Returns 201 + ingested status for new emails. "
        "Returns 200 + duplicate status for already-seen emails."
    ),
)
def ingest_email(
    file: UploadFile = File(..., description="RFC 2822 .eml file"),
    db: Session = Depends(get_db),
) -> IngestionSuccess | IngestionDuplicate:
    # Basic content-type guard (informational — not a hard security boundary)
    if file.content_type and file.content_type not in (
        "message/rfc822",
        "application/octet-stream",
        "text/plain",
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unexpected content type '{file.content_type}'. "
                "Upload a raw .eml file."
            ),
        )

    raw_bytes = file.file.read()

    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(raw_bytes) > MAX_EML_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_EML_SIZE_BYTES} bytes.",
        )

    try:
        result = ingest_eml(raw_bytes=raw_bytes, db=db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Return 200 for duplicates, 201 for new (FastAPI default is 201 from decorator)
    if isinstance(result, IngestionDuplicate):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result.model_dump(mode="json"),
        )

    return result
