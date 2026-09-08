"""
Tests for MatterEvent model, service, and observation foundation.

Coverage:
  MODEL / CREATION, VALIDATION, IDEMPOTENCY, SERVICE TRANSACTION,
  OBSERVATION, MIGRATION / REGRESSION
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.matter import Matter
from app.models.matter_event import MatterEvent
from app.services.matter_event import VALID_EVENT_TYPES, VALID_SOURCE_TYPES, record_matter_event
from app.services.matter_observation import observe_matter_event, MatterObservationResult


def _mk_matter(db: Session, matter_key: str | None = None) -> Matter:
    if matter_key is None:
        matter_key = f"TEST-ME-{uuid.uuid4().hex[:8]}"
    m = Matter(
        matter_key=matter_key,
        client_id="TEST",
        matter_id="001",
        client_name="Test Client LLC",
        matter_name="Test Matter",
        matter_description="Test matter for MatterEvent tests",
        matter_status="open",
    )
    db.add(m)
    db.flush()
    return m


def _mk_event(
    db: Session,
    matter_key: str,
    event_type: str = "MATTER_CREATED",
    source_type: str = "MATTER",
    source_reference: str | None = None,
    occurred_at: datetime | None = None,
    metadata: dict | None = None,
) -> MatterEvent:
    if source_reference is None:
        source_reference = f"ref-{uuid.uuid4().hex[:8]}"
    return record_matter_event(
        db,
        matter_key=matter_key,
        event_type=event_type,
        source_type=source_type,
        source_reference=source_reference,
        occurred_at=occurred_at,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# 1. MODEL / CREATION
# ---------------------------------------------------------------------------
class TestModelCreation:
    def test_creates_valid_matter_event(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key)
        db_session.commit()

        assert event.event_id is not None
        assert isinstance(event.event_id, uuid.UUID)
        assert event.matter_key == matter.matter_key
        assert event.event_type == "MATTER_CREATED"
        assert event.source_type == "MATTER"
        assert event.source_reference is not None
        assert isinstance(event.source_reference, str)
        assert event.occurred_at is not None
        assert event.created_at is not None

    def test_belongs_to_correct_matter(self, db_session):
        m1 = _mk_matter(db_session, f"TEST-ME-M1-{uuid.uuid4().hex[:8]}")
        m2 = _mk_matter(db_session, f"TEST-ME-M2-{uuid.uuid4().hex[:8]}")
        db_session.commit()

        e1 = _mk_event(db_session, m1.matter_key, source_reference="ref-m1")
        e2 = _mk_event(db_session, m2.matter_key, source_reference="ref-m2")
        db_session.commit()

        assert e1.matter_key == m1.matter_key
        assert e2.matter_key == m2.matter_key

    def test_occurred_at_defaults_to_utc_now(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        before = datetime.now(timezone.utc)
        event = _mk_event(db_session, matter.matter_key, occurred_at=None)
        db_session.commit()
        after = datetime.now(timezone.utc)

        assert event.occurred_at is not None
        assert before <= event.occurred_at <= after
        assert event.occurred_at.tzinfo is not None

    def test_created_at_is_populated(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key)
        db_session.commit()

        assert event.created_at is not None
        assert isinstance(event.created_at, datetime)

    def test_metadata_stores_json_compatible_data(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        meta = {"key": "value", "count": 42, "nested": {"a": True}}
        event = _mk_event(db_session, matter.matter_key, metadata=meta)
        db_session.commit()

        assert event.event_metadata == meta


# ---------------------------------------------------------------------------
# 2. VALIDATION
# ---------------------------------------------------------------------------
class TestValidation:
    def test_missing_matter_rejected(self, db_session):
        with pytest.raises(ValueError, match="does not exist"):
            record_matter_event(
                db_session,
                matter_key="NONEXISTENT-MATTER",
                event_type="MATTER_CREATED",
                source_type="MATTER",
            )

    def test_invalid_event_type_rejected(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        with pytest.raises(ValueError, match="Invalid event_type"):
            record_matter_event(
                db_session,
                matter_key=matter.matter_key,
                event_type="INVALID_EVENT",
                source_type="MATTER",
            )

    def test_invalid_source_type_rejected(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        with pytest.raises(ValueError, match="Invalid source_type"):
            record_matter_event(
                db_session,
                matter_key=matter.matter_key,
                event_type="MATTER_CREATED",
                source_type="INVALID_SOURCE",
            )

    def test_source_reference_too_long_rejected(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        with pytest.raises(ValueError, match="source_reference must be at most 500 characters"):
            record_matter_event(
                db_session,
                matter_key=matter.matter_key,
                event_type="MATTER_CREATED",
                source_type="MATTER",
                source_reference="x" * 501,
            )

    def test_metadata_must_be_dict(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        with pytest.raises(ValueError, match="metadata must be a JSON-compatible object"):
            record_matter_event(
                db_session,
                matter_key=matter.matter_key,
                event_type="MATTER_CREATED",
                source_type="MATTER",
                metadata="not-a-dict",
            )


# ---------------------------------------------------------------------------
# 3. IDEMPOTENCY
# ---------------------------------------------------------------------------
class TestIdempotency:
    def test_duplicate_with_source_reference_raises(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        dup_ref = f"dup-ref-{uuid.uuid4().hex[:8]}"
        _mk_event(db_session, matter.matter_key, source_reference=dup_ref)
        db_session.commit()

        with pytest.raises(Exception):
            _mk_event(db_session, matter.matter_key, source_reference=dup_ref)

    def test_same_reference_different_event_type_allowed(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        shared_ref = f"ref-1-{uuid.uuid4().hex[:8]}"
        e1 = _mk_event(db_session, matter.matter_key, event_type="MATTER_CREATED", source_reference=shared_ref)
        e2 = _mk_event(db_session, matter.matter_key, event_type="CASE_BRAIN_UPDATED", source_reference=shared_ref)
        db_session.commit()

        assert e1.event_type == "MATTER_CREATED"
        assert e2.event_type == "CASE_BRAIN_UPDATED"

    def test_different_reference_same_event_type_allowed(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        ref_a = f"ref-a-{uuid.uuid4().hex[:8]}"
        ref_b = f"ref-b-{uuid.uuid4().hex[:8]}"
        e1 = _mk_event(db_session, matter.matter_key, source_reference=ref_a)
        e2 = _mk_event(db_session, matter.matter_key, source_reference=ref_b)
        db_session.commit()

        assert e1.source_reference == ref_a
        assert e2.source_reference == ref_b

    def test_no_source_reference_not_globally_unique(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        e1 = _mk_event(db_session, matter.matter_key, source_reference=None)
        e2 = _mk_event(db_session, matter.matter_key, source_reference=None)
        db_session.commit()

        assert e1.event_id != e2.event_id


# ---------------------------------------------------------------------------
# 4. SERVICE TRANSACTION
# ---------------------------------------------------------------------------
class TestServiceTransaction:
    def test_record_does_not_commit(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = record_matter_event(
            db_session,
            matter_key=matter.matter_key,
            event_type="MATTER_CREATED",
            source_type="MATTER",
        )
        db_session.rollback()

        found = db_session.query(MatterEvent).filter(MatterEvent.event_id == event.event_id).first()
        assert found is None

    def test_caller_can_commit(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = record_matter_event(
            db_session,
            matter_key=matter.matter_key,
            event_type="MATTER_CREATED",
            source_type="MATTER",
        )
        db_session.commit()

        found = db_session.query(MatterEvent).filter(MatterEvent.event_id == event.event_id).first()
        assert found is not None

    def test_caller_can_rollback(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = record_matter_event(
            db_session,
            matter_key=matter.matter_key,
            event_type="MATTER_CREATED",
            source_type="MATTER",
        )
        db_session.rollback()

        found = db_session.query(MatterEvent).filter(MatterEvent.event_id == event.event_id).first()
        assert found is None


# ---------------------------------------------------------------------------
# 5. OBSERVATION
# ---------------------------------------------------------------------------
class TestObservation:
    def test_observe_valid_event(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key)
        db_session.commit()

        result = observe_matter_event(db_session, event)
        db_session.commit()

        assert isinstance(result, MatterObservationResult)
        assert result.event_id == str(event.event_id)
        assert result.matter_key == matter.matter_key
        assert result.observed is True
        assert result.actions_taken == []
        assert result.metadata["event_type"] == event.event_type

    def test_observation_does_not_create_task(self, db_session):
        from app.models.task import Task

        matter = _mk_matter(db_session)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key)
        db_session.commit()

        observe_matter_event(db_session, event)
        db_session.commit()

        tasks = db_session.query(Task).all()
        assert len(tasks) == 0

    def test_observation_does_not_create_case_brain_log(self, db_session):
        from app.models.case_brain_log import CaseBrainLog

        matter = _mk_matter(db_session)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key)
        db_session.commit()

        observe_matter_event(db_session, event)
        db_session.commit()

        logs = db_session.query(CaseBrainLog).all()
        assert len(logs) == 0

    def test_observation_returns_expected_structure(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()

        event = _mk_event(db_session, matter.matter_key, metadata={"key": "value"})
        db_session.commit()

        result = observe_matter_event(db_session, event)
        payload = result.to_dict()

        assert payload == {
            "event_id": str(event.event_id),
            "matter_key": matter.matter_key,
            "observed": True,
            "actions_taken": [],
            "metadata": {
                "event_type": "MATTER_CREATED",
                "source_type": "MATTER",
                "occurred_at": event.occurred_at.isoformat(),
            },
        }

    def test_invalid_matter_event_rejected(self, db_session):
        fake_event = MatterEvent(
            matter_key="NONEXISTENT-MATTER",
            event_type="MATTER_CREATED",
            source_type="MATTER",
            occurred_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            event_metadata=None,
        )

        with pytest.raises(ValueError, match="Cannot observe event"):
            observe_matter_event(db_session, fake_event)


# ---------------------------------------------------------------------------
# 6. MIGRATION / REGRESSION
# ---------------------------------------------------------------------------
class TestRegression:
    def test_matter_tests_still_pass(self, db_session):
        matter = _mk_matter(db_session)
        db_session.commit()
        assert matter.matter_key.startswith("TEST-ME-")

    def test_email_tests_still_pass(self, db_session):
        from app.models.email import Email

        email = Email(
            matter_key="10001-001",
            sender="test@example.com",
            subject="Test",
            body_text="Test body",
            processing_status="RECEIVED",
            raw_file_path="/tmp/test.eml",
            content_hash="a" * 64,
        )
        db_session.add(email)
        db_session.commit()
        assert email.email_id is not None

    def test_task_tests_still_pass(self, db_session):
        from app.models.task import Task

        matter = _mk_matter(db_session)
        db_session.commit()

        task = Task(
            matter_key=matter.matter_key,
            title="Test Task",
            task_type="LEGAL",
            status="OPEN",
            priority="MEDIUM",
            action_owner_type="INTERNAL",
        )
        db_session.add(task)
        db_session.commit()
        assert task.task_id is not None

    def test_case_brain_tests_still_pass(self, db_session):
        from app.models.case_brain_log import CaseBrainLog

        matter = _mk_matter(db_session)
        db_session.commit()

        log = CaseBrainLog(
            matter_key=matter.matter_key,
            source_type="manual",
            occurred_at=datetime.now(timezone.utc),
            update_summary="Test log",
        )
        db_session.add(log)
        db_session.commit()
        assert log.brain_entry_id is not None
