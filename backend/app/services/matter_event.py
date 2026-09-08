"""
Matter Event Service
====================

Responsibility:
  Record structured MatterEvent records for domain events.

Transaction rule:
  This service does NOT commit. The caller owns the transaction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.matter import Matter
from app.models.matter_event import MatterEvent


# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------
VALID_EVENT_TYPES = {
    "MATTER_CREATED",
    "EMAIL_RECEIVED",
    "EMAIL_ASSIGNED",
    "CASE_BRAIN_UPDATED",
}

VALID_SOURCE_TYPES = {
    "MATTER",
    "EMAIL",
    "CASE_BRAIN",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _validate_event_type(event_type: str) -> str:
    normalized = event_type.strip().upper()
    if normalized not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{event_type}'. "
            f"Allowed: {sorted(VALID_EVENT_TYPES)}"
        )
    return normalized


def _validate_source_type(source_type: str) -> str:
    normalized = source_type.strip().upper()
    if normalized not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_type '{source_type}'. "
            f"Allowed: {sorted(VALID_SOURCE_TYPES)}"
        )
    return normalized


def _validate_source_reference(source_reference: Optional[str]) -> Optional[str]:
    if source_reference is None:
        return None
    trimmed = source_reference.strip()
    if trimmed == "":
        return None
    if len(trimmed) > 500:
        raise ValueError("source_reference must be at most 500 characters.")
    return trimmed


def _validate_metadata(metadata: Any) -> Optional[dict]:
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return metadata
    raise ValueError("metadata must be a JSON-compatible object (dict) when provided.")


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def record_matter_event(
    db: Session,
    matter_key: str,
    event_type: str,
    source_type: str,
    source_reference: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> MatterEvent:
    """
    Record a new MatterEvent.

    Does NOT commit; the caller owns the transaction.
    """
    matter = db.get(Matter, matter_key.strip())
    if matter is None:
        raise ValueError(f"Matter '{matter_key}' does not exist.")

    validated_event_type = _validate_event_type(event_type)
    validated_source_type = _validate_source_type(source_type)
    validated_source_reference = _validate_source_reference(source_reference)
    validated_metadata = _validate_metadata(metadata)

    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)
    else:
        occurred_at = _ensure_utc(occurred_at)

    event = MatterEvent(
        matter_key=matter.matter_key,
        event_type=validated_event_type,
        source_type=validated_source_type,
        source_reference=validated_source_reference,
        occurred_at=occurred_at,
        created_at=datetime.now(timezone.utc),
        event_metadata=validated_metadata,
    )

    db.add(event)
    db.flush()
    db.refresh(event)
    return event
