"""
Matter Creation Service
=======================

Responsibility:
  Create a new Matter, optionally with initial participants and an optional
  opening intake narrative (Case Brain entry).

Transaction rule:
  This service does NOT commit. The caller owns the transaction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.case_brain_log import CaseBrainLog
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant
from app.schemas.matter_creation import (
    IntakeNarrative,
    MatterCreateRequest,
    MatterCreateResponse,
    MatterCaseBrainSummary,
    MatterParticipantSummary,
)
from app.services.case_brain import create_manual_case_brain_log


def _build_participant_summary(p: MatterParticipant) -> MatterParticipantSummary:
    return MatterParticipantSummary(
        participant_id=p.participant_id,
        matter_key=p.matter_key,
        participant_name=p.participant_name,
        email_address=p.email_address,
        organization=p.organization,
        role_relationship=p.role_relationship,
        is_active=p.is_active,
    )


def _build_case_brain_summary(entry: CaseBrainLog) -> MatterCaseBrainSummary:
    return MatterCaseBrainSummary(
        brain_entry_id=entry.brain_entry_id,
        email_id=str(entry.email_id) if entry.email_id is not None else None,
        occurred_at=entry.occurred_at,
        source_type=entry.source_type,
        source_reference=entry.source_reference,
        source_actor=entry.source_actor,
        update_summary=entry.update_summary,
        logged_by=entry.logged_by,
    )


def create_matter(
    db: Session,
    body: MatterCreateRequest,
) -> MatterCreateResponse:
    """
    Create a new Matter with optional participants and optional intake narrative.

    Raises:
        ValueError: if a Matter with the same matter_key already exists.

    Does NOT commit; the caller owns the transaction.
    """
    existing = db.get(Matter, body.matter_key)
    if existing is not None:
        raise ValueError(
            f"Matter '{body.matter_key}' already exists."
        )

    matter = Matter(
        matter_key=body.matter_key,
        client_id=body.client_id,
        matter_id=body.matter_id,
        client_name=body.client_name,
        matter_name=body.matter_name,
        matter_description=body.matter_description,
        matter_status=body.matter_status,
        practice_area=body.practice_area,
        matter_type=body.matter_type,
        matter_aliases_identifiers=body.matter_aliases_identifiers,
        primary_attorney=body.primary_attorney,
    )
    db.add(matter)
    db.flush()

    if body.participants:
        for participant in body.participants:
            p = MatterParticipant(
                matter_key=matter.matter_key,
                participant_name=participant.participant_name,
                email_address=participant.email_address,
                organization=participant.organization,
                role_relationship=participant.role_relationship,
                is_active=participant.is_active,
            )
            db.add(p)
        db.flush()

    case_brain_entries: list[CaseBrainLog] = []
    if body.intake_narrative is not None:
        narrative: IntakeNarrative = body.intake_narrative
        log_entry = create_manual_case_brain_log(
            db,
            matter.matter_key,
            source_type="intake",
            update_summary=narrative.update_summary,
            source_actor=narrative.source_actor,
            source_reference=narrative.source_reference,
            occurred_at=narrative.occurred_at,
            logged_by=narrative.logged_by,
        )
        db.flush()
        db.refresh(log_entry)
        case_brain_entries.append(log_entry)
        db.refresh(matter)

    participant_summaries = [
        _build_participant_summary(p) for p in matter.participants
    ]
    case_brain_summaries = [
        _build_case_brain_summary(e) for e in case_brain_entries
    ]

    return MatterCreateResponse(
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
        participants=participant_summaries,
        case_brain_entries=case_brain_summaries,
    )
