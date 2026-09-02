"""
Case Brain service helpers.

Shared logic for creating CaseBrainLog entries so that email ingestion and
manual Case Brain Entry authoring use the same conventions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.case_brain_log import CaseBrainLog
from app.models.email import Email
from app.models.matter import Matter


# Source types accepted by the manual entry path. "email" is reserved for
# the email ingestion writer and is rejected at the service boundary as
# defense-in-depth (the Pydantic schema also rejects it).
_MANUAL_SOURCE_TYPES = frozenset({"manual", "intake", "system", "import"})


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


def create_manual_case_brain_log(
    db: Session,
    matter_key: str,
    *,
    source_type: str,
    update_summary: str,
    source_reference: Optional[str] = None,
    source_actor: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
    logged_by: Optional[str] = None,
) -> CaseBrainLog:
    """
    Create a manually authored CaseBrainLog entry for an existing Matter.

    The email ingestion path is the only writer of source_type="EMAIL" rows;
    this writer explicitly rejects that value to enforce the separation.

    Manual entries are intentionally NOT idempotent. Two identical manual
    entries are allowed because a lawyer may legitimately record two
    separate events (e.g. two phone calls on the same topic).

    Raises:
        ValueError: if the Matter does not exist, or if source_type is
            not one of the accepted manual source types (or is "email").
        ValueError: if update_summary is empty or whitespace-only.

    Does NOT commit; the caller owns the transaction.
    """
    matter = db.get(Matter, matter_key)
    if matter is None:
        raise ValueError(f"Matter '{matter_key}' not found.")

    normalized_source = (source_type or "").strip().lower()
    if normalized_source == "email":
        raise ValueError(
            "source_type 'email' is reserved for the ingestion path and "
            "cannot be created via the manual entry endpoint."
        )
    if normalized_source not in _MANUAL_SOURCE_TYPES:
        raise ValueError(
            f"source_type must be one of {sorted(_MANUAL_SOURCE_TYPES)}."
        )

    if not update_summary or not update_summary.strip():
        raise ValueError("update_summary must not be empty or whitespace-only.")

    when = occurred_at or datetime.now(timezone.utc)

    log_entry = CaseBrainLog(
        matter_key=matter_key,
        email_id=None,
        occurred_at=when,
        source_type=normalized_source,
        source_reference=source_reference,
        source_actor=source_actor,
        update_summary=update_summary,
        logged_by=logged_by,
    )
    db.add(log_entry)

    matter.last_brain_update = datetime.now(timezone.utc)
    db.add(matter)

    db.flush()
    db.refresh(log_entry)
    return log_entry
