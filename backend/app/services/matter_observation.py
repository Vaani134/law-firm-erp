"""
Matter Observation Service
==========================

Minimal observation foundation for MatterEvent records.

T7 responsibility:
  - Accept a MatterEvent
  - Validate that the event belongs to an existing Matter
  - Return a structured observation result
  - Provide a clean extension point for future automation rules (T8+)

This service does NOT:
  - create Tasks
  - modify Case Brain
  - invoke AI/LLM
  - commit transactions
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.matter import Matter
from app.models.matter_event import MatterEvent


class MatterObservationResult:
    """Structured result returned by observe_matter_event."""

    def __init__(
        self,
        event_id: str,
        matter_key: str,
        observed: bool,
        actions_taken: list[str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.event_id = event_id
        self.matter_key = matter_key
        self.observed = observed
        self.actions_taken = actions_taken
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "matter_key": self.matter_key,
            "observed": self.observed,
            "actions_taken": self.actions_taken,
            "metadata": self.metadata,
        }


def observe_matter_event(
    db: Session,
    event: MatterEvent,
) -> MatterObservationResult:
    """
    Observe a MatterEvent and return a structured result.

    For T7 this is intentionally minimal. Future T8+ rules will extend
    this function to trigger task automation, notifications, etc.

    Does NOT commit; the caller owns the transaction.
    """
    matter = db.get(Matter, event.matter_key)
    if matter is None:
        raise ValueError(
            f"Cannot observe event {event.event_id}: "
            f"Matter '{event.matter_key}' does not exist."
        )

    result = MatterObservationResult(
        event_id=str(event.event_id),
        matter_key=event.matter_key,
        observed=True,
        actions_taken=[],
        metadata={
            "event_type": event.event_type,
            "source_type": event.source_type,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        },
    )

    return result
