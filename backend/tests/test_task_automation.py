"""
Tests for Task Automation Rules.

Coverage:
  RULE MODEL, MATCHING, CONDITIONS, TASK CREATION, PROVENANCE,
  IDEMPOTENCY, TRANSACTION, REGRESSION
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.matter import Matter
from app.models.matter_event import MatterEvent
from app.models.task import Task
from app.models.task_automation_rule import TaskAutomationRule
from app.services.matter_event import record_matter_event
from app.services.task_automation import (
    AutomationResult,
    evaluate_event_for_task_automation,
)


def _mk_matter(db: Session, matter_key: str | None = None, **overrides) -> Matter:
    if matter_key is None:
        matter_key = f"TEST-TA-{uuid.uuid4().hex[:8]}"
    defaults = {
        "client_id": "TEST",
        "matter_id": "001",
        "client_name": "Test Client LLC",
        "matter_name": "Test Matter",
        "matter_description": "Test matter for automation tests",
        "matter_status": "open",
        "practice_area": "Litigation",
    }
    defaults.update(overrides)
    m = Matter(matter_key=matter_key, **defaults)
    db.add(m)
    db.flush()
    return m


def _mk_event(
    db: Session,
    matter_key: str,
    event_type: str = "MATTER_CREATED",
    source_type: str = "MATTER",
    source_reference: str | None = None,
) -> MatterEvent:
    if source_reference is None:
        source_reference = f"ref-{uuid.uuid4().hex[:8]}"
    return record_matter_event(
        db,
        matter_key=matter_key,
        event_type=event_type,
        source_type=source_type,
        source_reference=source_reference,
    )


def _mk_rule(
    db: Session,
    rule_key: str,
    event_type: str = "MATTER_CREATED",
    source_type: str | None = None,
    conditions: dict | None = None,
    task_template: dict | None = None,
    is_active: bool = True,
) -> TaskAutomationRule:
    if task_template is None:
        task_template = {
            "title": "Automated Task",
            "task_type": "LEGAL",
            "priority": "MEDIUM",
            "action_owner_type": "INTERNAL",
        }
    rule = TaskAutomationRule(
        rule_id=str(uuid.uuid4()),
        rule_key=rule_key,
        rule_name=f"Rule {rule_key}",
        event_type=event_type,
        source_type=source_type,
        is_active=is_active,
        conditions=conditions,
        task_template=task_template,
    )
    db.add(rule)
    db.flush()
    return rule


# ---------------------------------------------------------------------------
# A. Rule model creation
# ---------------------------------------------------------------------------
class TestRuleModelCreation:
    def test_creates_valid_rule(self, db_session):
        rule = _mk_rule(db_session, f"RULE-{uuid.uuid4().hex[:8]}")
        db_session.commit()

        assert rule.rule_id is not None
        assert rule.rule_key.startswith("RULE-")
        assert rule.is_active is True
        assert rule.event_type == "MATTER_CREATED"
        assert rule.source_type is None

    def test_rule_with_source_type(self, db_session):
        rule = _mk_rule(db_session, f"SRC-{uuid.uuid4().hex[:8]}", source_type="EMAIL")
        db_session.commit()

        assert rule.source_type == "EMAIL"

    def test_rule_with_conditions(self, db_session):
        cond = {"practice_area": "Litigation"}
        rule = _mk_rule(db_session, f"COND-{uuid.uuid4().hex[:8]}", conditions=cond)
        db_session.commit()

        assert rule.conditions == cond

    def test_rule_with_task_template(self, db_session):
        template = {
            "title": "Review contract",
            "task_type": "LEGAL",
            "priority": "HIGH",
            "action_owner_type": "INTERNAL",
        }
        rule = _mk_rule(db_session, f"TPL-{uuid.uuid4().hex[:8]}", task_template=template)
        db_session.commit()

        assert rule.task_template == template


# ---------------------------------------------------------------------------
# B. Active rule matching event_type
# ---------------------------------------------------------------------------
class TestActiveRuleMatching:
    def test_active_rule_matches_event_type(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        _mk_rule(db_session, f"MATCH-EVT-{uuid.uuid4().hex[:8]}", event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_evaluated == 1
        assert result.rules_matched == 1
        assert result.tasks_created == 1

    def test_inactive_rule_not_evaluated(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        _mk_rule(db_session, f"INACTIVE-{uuid.uuid4().hex[:8]}", event_type="MATTER_CREATED", is_active=False)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_evaluated == 0
        assert result.rules_matched == 0
        assert result.tasks_created == 0


# ---------------------------------------------------------------------------
# C. source_type matching
# ---------------------------------------------------------------------------
class TestSourceTypeMatching:
    def test_matching_source_type(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        _mk_rule(db_session, f"SRC-MATCH-{uuid.uuid4().hex[:8]}", event_type="EMAIL_RECEIVED", source_type="EMAIL")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="EMAIL_RECEIVED", source_type="EMAIL")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 1
        assert result.tasks_created == 1

    def test_mismatched_source_type(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        _mk_rule(db_session, f"SRC-MISMATCH-{uuid.uuid4().hex[:8]}", event_type="EMAIL_RECEIVED", source_type="EMAIL")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="EMAIL_RECEIVED", source_type="CASE_BRAIN")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 0
        assert result.tasks_created == 0


# ---------------------------------------------------------------------------
# D. Condition matching
# ---------------------------------------------------------------------------
class TestConditionMatching:
    def test_exact_condition_match(self, db_session):
        matter = _mk_matter(db_session, practice_area="Litigation")
        db_session.commit()

        _mk_rule(
            db_session,
            f"COND-MATCH-{uuid.uuid4().hex[:8]}",
            event_type="MATTER_CREATED",
            conditions={"practice_area": "Litigation"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 1
        assert result.tasks_created == 1

    def test_multiple_condition_match(self, db_session):
        matter = _mk_matter(db_session, practice_area="Litigation", matter_status="open")
        db_session.commit()

        _mk_rule(
            db_session,
            f"COND-MULTI-{uuid.uuid4().hex[:8]}",
            event_type="MATTER_CREATED",
            conditions={"practice_area": "Litigation", "matter_status": "open"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 1
        assert result.tasks_created == 1

    def test_condition_mismatch(self, db_session):
        matter = _mk_matter(db_session, practice_area="Corporate")
        db_session.commit()

        _mk_rule(
            db_session,
            f"COND-MISMATCH-{uuid.uuid4().hex[:8]}",
            event_type="MATTER_CREATED",
            conditions={"practice_area": "Litigation"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 0
        assert result.tasks_created == 0

    def test_unknown_condition_field_no_match(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        _mk_rule(
            db_session,
            f"COND-UNKNOWN-{uuid.uuid4().hex[:8]}",
            event_type="MATTER_CREATED",
            conditions={"unknown_field": "value"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 0
        assert result.tasks_created == 0


# ---------------------------------------------------------------------------
# E. Automated task creation
# ---------------------------------------------------------------------------
class TestAutomatedTaskCreation:
    def test_creates_task_from_template(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        template = {
            "title": "Conduct initial case assessment",
            "task_type": "LEGAL",
            "priority": "HIGH",
            "action_owner_type": "INTERNAL",
        }
        rule_key = f"CREATE-TASK-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED", task_template=template)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.tasks_created == 1
        assert len(result.created_task_ids) == 1

        task = db_session.query(Task).filter(Task.task_id == result.created_task_ids[0]).first()
        assert task is not None
        assert task.title == "Conduct initial case assessment"
        assert task.task_type == "LEGAL"
        assert task.priority == "HIGH"

    def test_task_receives_correct_provenance(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"PROV-RULE-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED", source_type="EMAIL", source_reference="ref-1")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        task = db_session.query(Task).filter(Task.task_id == result.created_task_ids[0]).first()
        assert task.creation_source == "AUTOMATED"
        assert task.automation_rule_key == rule_key
        assert task.source_type == "EMAIL"
        assert task.source_reference == "ref-1"

    def test_automation_event_id_stored(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"EVT-ID-RULE-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        task = db_session.query(Task).filter(Task.task_id == result.created_task_ids[0]).first()
        assert task.automation_event_id == str(event.event_id)


# ---------------------------------------------------------------------------
# F. Idempotency
# ---------------------------------------------------------------------------
class TestIdempotency:
    def test_same_event_same_rule_only_one_task(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"IDEM-1-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        r1 = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        r2 = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert r1.tasks_created == 1
        assert r2.tasks_created == 0
        assert r2.tasks_skipped_duplicate == 1

        total = db_session.query(Task).filter(Task.automation_rule_key == rule_key).count()
        assert total == 1

    def test_same_event_two_rules_two_tasks(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_a = f"IDEM-A-{uuid.uuid4().hex[:8]}"
        rule_b = f"IDEM-B-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_a, event_type="MATTER_CREATED")
        _mk_rule(db_session, rule_b, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.tasks_created == 2
        assert len(result.created_task_ids) == 2
        assert rule_a in result.matched_rule_keys
        assert rule_b in result.matched_rule_keys


# ---------------------------------------------------------------------------
# G. Missing/invalid template
# ---------------------------------------------------------------------------
class TestInvalidTemplate:
    def test_missing_title_raises(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"NO-TITLE-{uuid.uuid4().hex[:8]}"
        _mk_rule(
            db_session,
            rule_key,
            event_type="MATTER_CREATED",
            task_template={"task_type": "LEGAL"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        with pytest.raises(ValueError, match="non-empty 'title'"):
            evaluate_event_for_task_automation(db_session, event)

    def test_waiting_without_waiting_on_raises(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"WAIT-{uuid.uuid4().hex[:8]}"
        template = {
            "title": "Waiting Task",
            "task_type": "LEGAL",
            "status": "WAITING",
            "action_owner_type": "INTERNAL",
        }
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED", task_template=template)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        with pytest.raises(ValueError, match="waiting_on is required"):
            evaluate_event_for_task_automation(db_session, event)


# ---------------------------------------------------------------------------
# G+. Failure behavior hardening
# ---------------------------------------------------------------------------
class TestFailureBehavior:
    def test_malformed_template_raises_not_silent(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"MALFORMED-{uuid.uuid4().hex[:8]}"
        _mk_rule(
            db_session,
            rule_key,
            event_type="MATTER_CREATED",
            task_template={"task_type": "LEGAL"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        with pytest.raises(ValueError):
            evaluate_event_for_task_automation(db_session, event)

    def test_unexpected_failure_propagates(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"UNEXPECT-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        original_query = db_session.query

        def failing_query(*args, **kwargs):
            raise RuntimeError("Simulated unexpected failure")

        db_session.query = failing_query  # type: ignore[assignment]
        try:
            with pytest.raises(RuntimeError, match="Simulated unexpected failure"):
                evaluate_event_for_task_automation(db_session, event)
        finally:
            db_session.query = original_query  # type: ignore[assignment]

    def test_valid_matching_rule_creates_task(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"VALID-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.tasks_created == 1
        assert result.rules_matched == 1

    def test_nonmatching_rule_does_nothing(self, db_session):
        matter = _mk_matter(db_session, practice_area="Corporate")
        db_session.commit()

        rule_key = f"NOMATCH-{uuid.uuid4().hex[:8]}"
        _mk_rule(
            db_session,
            rule_key,
            event_type="MATTER_CREATED",
            conditions={"practice_area": "Litigation"},
        )
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.rules_matched == 0
        assert result.tasks_created == 0

    def test_multiple_matching_rules_create_expected_tasks(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_a = f"MULTI-A-{uuid.uuid4().hex[:8]}"
        rule_b = f"MULTI-B-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_a, event_type="MATTER_CREATED")
        _mk_rule(db_session, rule_b, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert result.tasks_created == 2
        assert result.rules_matched == 2
        assert rule_a in result.matched_rule_keys
        assert rule_b in result.matched_rule_keys

    def test_idempotency_remains_intact_after_template_fix(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"IDEM-FIX-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        r1 = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        r2 = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        assert r1.tasks_created == 1
        assert r2.tasks_created == 0
        assert r2.tasks_skipped_duplicate == 1
        total = db_session.query(Task).filter(Task.automation_rule_key == rule_key).count()
        assert total == 1


# ---------------------------------------------------------------------------
# H. Service does not commit
# ---------------------------------------------------------------------------
class TestServiceTransaction:
    def test_does_not_commit(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"NO-COMMIT-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        evaluate_event_for_task_automation(db_session, event)
        db_session.rollback()

        count = db_session.query(Task).count()
        assert count == 0


# ---------------------------------------------------------------------------
# I. Existing manual Task creation still works
# ---------------------------------------------------------------------------
class TestManualTaskCreation:
    def test_manual_task_defaults(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        task = Task(
            matter_key=matter.matter_key,
            title="Manual Task",
            task_type="LEGAL",
            status="OPEN",
            priority="MEDIUM",
            action_owner_type="INTERNAL",
        )
        db_session.add(task)
        db_session.commit()

        assert task.creation_source == "MANUAL"
        assert task.automation_rule_key is None
        assert task.automation_event_id is None


# ---------------------------------------------------------------------------
# J. Transaction rollback does not leave automated task
# ---------------------------------------------------------------------------
class TestTransactionRollback:
    def test_rollback_clears_automated_task(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"ROLLBACK-RULE-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        evaluate_event_for_task_automation(db_session, event)
        db_session.rollback()

        count = db_session.query(Task).count()
        assert count == 0


# ---------------------------------------------------------------------------
# K. Existing Task lifecycle behavior intact
# ---------------------------------------------------------------------------
class TestTaskLifecycleIntact:
    def test_waiting_without_waiting_on_raises(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"WAIT-RULE-{uuid.uuid4().hex[:8]}"
        template = {
            "title": "Waiting Task",
            "task_type": "LEGAL",
            "status": "WAITING",
            "action_owner_type": "INTERNAL",
        }
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED", task_template=template)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        with pytest.raises(ValueError, match="waiting_on is required"):
            evaluate_event_for_task_automation(db_session, event)

    def test_completion_sets_timestamp(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        rule_key = f"COMPLETE-RULE-{uuid.uuid4().hex[:8]}"
        _mk_rule(db_session, rule_key, event_type="MATTER_CREATED")
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED")
        db_session.commit()

        result = evaluate_event_for_task_automation(db_session, event)
        db_session.commit()

        task = db_session.query(Task).filter(Task.task_id == result.created_task_ids[0]).first()
        assert task.status == "OPEN"
        assert task.completed_at is None
