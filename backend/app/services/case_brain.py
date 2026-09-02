"""
Case Brain service helpers.

Shared logic for creating CaseBrainLog entries so that email ingestion and
manual Matter Resolution use the same conventions and idempotency rules.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email


def create_case_brain_log(
    db: Session,
    email_row: Email,
    matter_key: str,
    update_summary: str | None = None,
) -> None:
    """
    Create a CaseBrainLog entry for a successfully resolved email.

    Idempotent: if a log entry already exists for this email_id, no-op.
    Does NOT commit; the caller owns the transaction.
    """
    existing = db.query(CaseBrainLog).filter(CaseBrainLog.email_id == email_row.email_id).first()
    if existing:
        return

    if update_summary is None:
        update_summary = f"Email received and associated with Matter {matter_key}"

    log_entry = CaseBrainLog(
        matter_key=matter_key,
        email_id=email_row.email_id,
        occurred_at=email_row.received_at or datetime.now(timezone.utc),
        source_type="EMAIL",
        source_reference=email_row.message_id,
        source_actor=email_row.sender,
        update_summary=update_summary,
        logged_by=None,
    )
    db.add(log_entry)
