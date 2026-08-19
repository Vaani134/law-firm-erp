"""
GET /api/matters/{matter_key}

Read-only endpoint that returns the complete Matter detail including
participants, emails, and Case Brain timeline.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant
from app.schemas.matter_detail import (
    MatterCaseBrainEntry,
    MatterDetailResponse,
    MatterEmailResponse,
    MatterParticipantResponse,
    MatterResponse,
)

router = APIRouter(prefix="/api/matters", tags=["Matter Detail"])


@router.get(
    "/{matter_key}",
    response_model=MatterDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Matter detail",
    description=(
        "Returns the complete detail for the specified Matter, including "
        "participants, associated emails, and Case Brain timeline entries. "
        "If the Matter does not exist, returns 404."
    ),
)
def get_matter_detail(
    matter_key: str,
    db: Session = Depends(get_db),
) -> MatterDetailResponse:
    matter = db.get(Matter, matter_key)
    if matter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matter not found",
        )

    participants = (
        db.query(MatterParticipant)
        .filter(MatterParticipant.matter_key == matter_key)
        .order_by(MatterParticipant.participant_id.asc())
        .all()
    )

    emails = (
        db.query(Email)
        .filter(Email.matter_key == matter_key)
        .order_by(Email.created_at.asc(), Email.email_id.asc())
        .all()
    )

    case_brain_entries = (
        db.query(CaseBrainLog)
        .filter(CaseBrainLog.matter_key == matter_key)
        .order_by(CaseBrainLog.occurred_at.asc(), CaseBrainLog.brain_entry_id.asc())
        .all()
    )

    return MatterDetailResponse(
        matter=MatterResponse(
            matter_key=matter.matter_key,
            client_id=matter.client_id,
            matter_id=matter.matter_id,
            client_name=matter.client_name,
            matter_name=matter.matter_name,
            practice_area=matter.practice_area,
            matter_type=matter.matter_type,
            matter_description=matter.matter_description,
            matter_aliases_identifiers=matter.matter_aliases_identifiers,
            matter_status=matter.matter_status,
            primary_attorney=matter.primary_attorney,
            last_brain_update=matter.last_brain_update,
            created_at=matter.created_at,
            updated_at=matter.updated_at,
        ),
        participants=[
            MatterParticipantResponse(
                participant_id=p.participant_id,
                matter_key=p.matter_key,
                participant_name=p.participant_name,
                email_address=p.email_address,
                organization=p.organization,
                role_relationship=p.role_relationship,
                is_active=p.is_active,
            )
            for p in participants
        ],
        emails=[
            MatterEmailResponse(
                email_id=str(e.email_id),
                message_id=e.message_id,
                matter_key=e.matter_key,
                sender=e.sender,
                to_recipients=e.to_recipients,
                cc_recipients=e.cc_recipients,
                subject=e.subject,
                body_text=e.body_text,
                received_at=e.received_at,
                raw_file_path=e.raw_file_path,
                content_hash=e.content_hash,
                processing_status=e.processing_status,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in emails
        ],
        case_brain=[
            MatterCaseBrainEntry(
                brain_entry_id=entry.brain_entry_id,
                email_id=entry.email_id,
                occurred_at=entry.occurred_at,
                source_type=entry.source_type,
                source_reference=entry.source_reference,
                source_actor=entry.source_actor,
                update_summary=entry.update_summary,
                logged_by=entry.logged_by,
            )
            for entry in case_brain_entries
        ],
    )
