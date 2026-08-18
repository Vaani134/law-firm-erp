"""
Matter Resolution Service
=========================

Responsibility:
  Given an email_id, attempt to identify which Matter the email belongs to
  by comparing the email's sender and recipient addresses against the
  matter_participants table.

MVP-0 resolution logic — exact email address match only:
  1. Collect all email addresses from the email's sender, to_recipients,
     and cc_recipients fields.
  2. Query matter_participants for any active participant whose email_address
     exactly matches one of those addresses (case-insensitive).
  3. If exactly one distinct Matter is found → assign it.
  4. If multiple distinct Matters are found → leave unresolved (ambiguous).
  5. If no match → leave unresolved.

Processing status updates:
  Successfully resolved  → MATTER_IDENTIFIED
  No match / ambiguous   → status unchanged (remains RECEIVED or whatever
                           it was when resolution ran)

What this service does NOT do:
  - Fuzzy / semantic matching
  - LLM / AI calls
  - Case Brain updates
  - Background tasks
  - Authentication
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.matter_participant import MatterParticipant
from app.schemas.matter_resolution import ResolutionResult

# Status written to the email row when a match is found.
# Taken directly from the approved vocabulary:
# RECEIVED | PROCESSING | MATTER_IDENTIFIED | ANALYZED |
# COMPLETED | REVIEW_REQUIRED | FAILED
STATUS_RESOLVED = "MATTER_IDENTIFIED"


def _collect_addresses(email_row: Email) -> set[str]:
    """
    Return a lower-cased set of all email addresses visible on the message:
    sender, To recipients, and CC recipients.
    """
    addresses: set[str] = set()

    if email_row.sender:
        addresses.add(email_row.sender.strip().lower())

    for field in (email_row.to_recipients, email_row.cc_recipients):
        if field:                               # JSONB list of {"name", "email"} dicts
            for entry in field:
                addr = entry.get("email", "").strip().lower()
                if addr:
                    addresses.add(addr)

    return addresses


def resolve_matter(
    email_id: uuid.UUID,
    db: Session,
) -> ResolutionResult:
    """
    Attempt to resolve an email to a Matter.

    Returns a ResolutionResult schema object.
    Raises ValueError if the email_id does not exist.
    """
    email_row = db.get(Email, email_id)
    if email_row is None:
        raise ValueError(f"Email '{email_id}' not found.")

    # Already resolved — return current state without touching anything.
    if email_row.matter_key is not None:
        return ResolutionResult(
            email_id=email_row.email_id,
            status="already_resolved",
            matter_key=email_row.matter_key,
            match_found=True,
            processing_status=email_row.processing_status,
        )

    addresses = _collect_addresses(email_row)

    if not addresses:
        # No addresses to match against — leave unresolved.
        return ResolutionResult(
            email_id=email_row.email_id,
            status="unresolved",
            matter_key=None,
            match_found=False,
            processing_status=email_row.processing_status,
        )

    # Find active participants whose email_address matches any address on the email.
    # Compare case-insensitively by lower-casing both sides.
    matching_participants = (
        db.query(MatterParticipant)
        .filter(
            MatterParticipant.is_active.is_(True),
            MatterParticipant.email_address.isnot(None),
        )
        .all()
    )

    matched_matter_keys: set[str] = set()
    for participant in matching_participants:
        if participant.email_address.strip().lower() in addresses:
            matched_matter_keys.add(participant.matter_key)

    if len(matched_matter_keys) == 1:
        # Unambiguous match — assign and update status.
        resolved_key = next(iter(matched_matter_keys))
        email_row.matter_key = resolved_key
        email_row.processing_status = STATUS_RESOLVED
        db.commit()
        db.refresh(email_row)

        return ResolutionResult(
            email_id=email_row.email_id,
            status="resolved",
            matter_key=resolved_key,
            match_found=True,
            processing_status=email_row.processing_status,
        )

    # Zero matches or ambiguous (>1 distinct Matter) — leave unchanged.
    return ResolutionResult(
        email_id=email_row.email_id,
        status="unresolved",
        matter_key=None,
        match_found=False,
        processing_status=email_row.processing_status,
    )
