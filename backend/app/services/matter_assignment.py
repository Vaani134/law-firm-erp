"""
Matter Assignment Service
=========================

Responsibility:
  Manually assign an already-ingested email to a specific Matter.

This is distinct from automatic Matter Resolution:
  - POST /api/emails/{email_id}/resolve  → automatic participant-based matching
  - POST /api/emails/{email_id}/assign-matter  → explicit human assignment

Transaction rule:
  This service does NOT commit. The caller owns the transaction.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter
from app.services.case_brain import create_case_brain_log


def assign_matter(
    email_id: uuid.UUID,
    matter_key: str,
    db: Session,
) -> str:
    """
    Manually assign an email to a Matter.

    Returns one of:
      "assigned"         — email.matter_key was updated, CaseBrainLog created
      "already_assigned" — email already belongs to the requested Matter
      "conflict"         — email already belongs to a different Matter

    Raises ValueError if the email or Matter does not exist.
    Does NOT commit; the caller owns the transaction.
    """
    email_row = db.get(Email, email_id)
    if email_row is None:
        raise ValueError(f"Email '{email_id}' not found.")

    matter = db.get(Matter, matter_key)
    if matter is None:
        raise ValueError(f"Matter '{matter_key}' not found.")

    if email_row.matter_key is not None:
        if email_row.matter_key == matter_key:
            return "already_assigned"
        return "conflict"

    email_row.matter_key = matter_key
    email_row.processing_status = "MATTER_IDENTIFIED"
    create_case_brain_log(
        db,
        email_row,
        matter_key,
        update_summary=f"Email manually associated with Matter {matter_key}",
    )
    return "assigned"
