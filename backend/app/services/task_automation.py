"""
Task Automation Service
=======================

Deterministic rule evaluation for MatterEvent records.

Conceptual boundaries
---------------------
MatterEvent  : immutable-ish record of a domain fact — "what happened".
Observation  : interpretation/observation generated from an event.
Automation   : deterministic policy deciding whether an action should be generated.
Task         : actionable work item created by automation (or manually).
Case Brain   : matter-level memory/timeline, distinct from the event log.

Transaction rule:
  This service does NOT commit. The caller owns the transaction.

Error semantics:
  - A rule that does not match conditions is normal and returns no task.
  - A rule whose task template is malformed is a configuration error and
    MUST NOT be silently swallowed. The ValueError raised by template
    validation propagates to the caller so the transaction can roll back
    and the misconfiguration can be fixed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.matter import Matter
from app.models.matter_event import MatterEvent
from app.models.task import Task
from app.models.task_automation_rule import TaskAutomationRule


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
class AutomationResult:
    """Structured result returned by evaluate_event_for_task_automation."""

    def __init__(
        self,
        event_id: str,
        rules_evaluated: int,
        rules_matched: int,
        tasks_created: int,
        tasks_skipped_duplicate: int,
        matched_rule_keys: list[str],
        created_task_ids: list[str],
    ) -> None:
        self.event_id = event_id
        self.rules_evaluated = rules_evaluated
        self.rules_matched = rules_matched
        self.tasks_created = tasks_created
        self.tasks_skipped_duplicate = tasks_skipped_duplicate
        self.matched_rule_keys = matched_rule_keys
        self.created_task_ids = created_task_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "rules_evaluated": self.rules_evaluated,
            "rules_matched": self.rules_matched,
            "tasks_created": self.tasks_created,
            "tasks_skipped_duplicate": self.tasks_skipped_duplicate,
            "matched_rule_keys": self.matched_rule_keys,
            "created_task_ids": self.created_task_ids,
        }


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
def _build_event_context(event: MatterEvent, matter: Optional[Matter]) -> dict[str, Any]:
    """Build a deterministic flat context for condition evaluation."""
    ctx: dict[str, Any] = {
        "event_id": str(event.event_id),
        "matter_key": event.matter_key,
        "event_type": event.event_type,
        "source_type": event.source_type,
        "source_reference": event.source_reference,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
    }
    if matter is not None:
        ctx.update(
            {
                "client_name": matter.client_name,
                "matter_name": matter.matter_name,
                "matter_status": matter.matter_status,
                "practice_area": matter.practice_area,
                "matter_type": matter.matter_type,
            }
        )
    return ctx


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------
def _normalize(value: Any) -> Any:
    """Normalize values for case-insensitive string comparison."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _evaluate_conditions(
    conditions: Optional[dict[str, Any]],
    context: dict[str, Any],
) -> bool:
    """Evaluate flat exact-match conditions against context.

    All conditions must match for the rule to fire.
    If a condition references a missing context field, the rule does NOT match.
    """
    if not conditions:
        return True

    for key, expected in conditions.items():
        if key not in context:
            return False
        actual = _normalize(context[key])
        if actual != _normalize(expected):
            return False
    return True


# ---------------------------------------------------------------------------
# Task template application
# ---------------------------------------------------------------------------
def _parse_datetime(value: Any) -> Optional[datetime]:
    """Safely parse ISO-8601 datetime strings."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


def _apply_task_template(
    db: Session,
    matter: Matter,
    template: dict[str, Any],
    provenance: dict[str, Any],
) -> Task:
    """Create a Task from a rule's task_template.

    Does NOT commit; the caller owns the transaction.
    """
    title = template.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError("Task template must include a non-empty 'title'.")

    status = template.get("status", "OPEN")
    waiting_on = template.get("waiting_on")
    if status == "WAITING" and not waiting_on:
        raise ValueError("waiting_on is required when status is WAITING.")

    task = Task(
        matter_key=matter.matter_key,
        title=title.strip(),
        description=template.get("description"),
        task_type=template.get("task_type", "LEGAL"),
        status=status,
        priority=template.get("priority", "MEDIUM"),
        assigned_to=template.get("assigned_to"),
        created_by=template.get("created_by"),
        action_owner_type=template.get("action_owner_type", "INTERNAL"),
        waiting_on=waiting_on,
        waiting_reason=template.get("waiting_reason"),
        waiting_since=template.get("waiting_since"),
        due_at=_parse_datetime(template.get("due_at")),
        next_action_at=_parse_datetime(template.get("next_action_at")),
        creation_source=provenance["creation_source"],
        automation_rule_key=provenance["automation_rule_key"],
        source_type=provenance["source_type"],
        source_reference=provenance["source_reference"],
        automation_event_id=provenance["automation_event_id"],
    )

    if task.status == "WAITING" and task.waiting_since is None:
        task.waiting_since = datetime.now(timezone.utc)
    if task.status == "COMPLETED":
        task.completed_at = datetime.now(timezone.utc)

    db.add(task)
    db.flush()
    db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def evaluate_event_for_task_automation(
    db: Session,
    event: MatterEvent,
) -> AutomationResult:
    """
    Evaluate active automation rules against a MatterEvent and create Tasks.

    Does NOT commit; the caller owns the transaction.
    """
    matter = db.get(Matter, event.matter_key)
    if matter is None:
        raise ValueError(
            f"Cannot evaluate automation for event {event.event_id}: "
            f"Matter '{event.matter_key}' does not exist."
        )

    context = _build_event_context(event, matter)

    rules = (
        db.query(TaskAutomationRule)
        .filter(TaskAutomationRule.event_type == event.event_type)
        .filter(TaskAutomationRule.is_active.is_(True))
        .all()
    )

    rules_evaluated = len(rules)
    rules_matched = 0
    tasks_created = 0
    tasks_skipped_duplicate = 0
    matched_rule_keys: list[str] = []
    created_task_ids: list[str] = []

    for rule in rules:
        if rule.source_type is not None and rule.source_type != event.source_type:
            continue

        if not _evaluate_conditions(rule.conditions, context):
            continue

        rules_matched += 1
        matched_rule_keys.append(rule.rule_key)

        existing = (
            db.query(Task)
            .filter(
                Task.automation_event_id == str(event.event_id),
                Task.automation_rule_key == rule.rule_key,
            )
            .first()
        )
        if existing is not None:
            tasks_skipped_duplicate += 1
            continue

        provenance = {
            "creation_source": "AUTOMATED",
            "automation_rule_key": rule.rule_key,
            "source_type": event.source_type,
            "source_reference": event.source_reference,
            "automation_event_id": str(event.event_id),
        }

        task = _apply_task_template(db, matter, rule.task_template, provenance)

        tasks_created += 1
        created_task_ids.append(str(task.task_id))

    return AutomationResult(
        event_id=str(event.event_id),
        rules_evaluated=rules_evaluated,
        rules_matched=rules_matched,
        tasks_created=tasks_created,
        tasks_skipped_duplicate=tasks_skipped_duplicate,
        matched_rule_keys=matched_rule_keys,
        created_task_ids=created_task_ids,
    )
