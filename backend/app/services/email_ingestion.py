"""
Email Ingestion Service
=======================

Responsibility:
  Accept a raw .eml file, parse it, persist it to the database,
  and store the raw file on disk.

What this service does NOT do:
  - Matter Resolution
  - Case Brain updates
  - AI / LLM calls
  - Background task scheduling
  - Authentication

Processing status on new ingest: RECEIVED
(Matches the approved processing_status vocabulary:
 RECEIVED | PROCESSING | MATTER_IDENTIFIED | ANALYZED |
 COMPLETED | REVIEW_REQUIRED | FAILED)
"""

from __future__ import annotations

import email as stdlib_email
import email.policy
import email.utils
import hashlib
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.email import Email
from app.schemas.email_ingestion import IngestionDuplicate, IngestionSuccess

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROCESSING_STATUS_NEW = "RECEIVED"

# Root of the project — config.py is at <root>/backend/app/config.py
_PROJECT_ROOT = Path(settings.__class__.model_fields["database_url"].__class__.__module__  # fallback
                     if False else __file__).resolve().parent.parent.parent.parent
# Simpler, reliable derivation:
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # backend/app/services → root

# Ingested files live here — separate from test fixtures in data/emails/matter_1/
INGESTED_EMAIL_DIR = _PROJECT_ROOT / "data" / "emails" / "ingested"


# ---------------------------------------------------------------------------
# Internal dataclass — parsed email fields before DB write
# ---------------------------------------------------------------------------
@dataclass
class ParsedEmail:
    message_id: Optional[str]
    sender: str
    to_recipients: list[dict]
    cc_recipients: list[dict]
    subject: Optional[str]
    body_text: Optional[str]
    received_at: Optional[datetime]
    content_hash: str
    raw_bytes: bytes


# ---------------------------------------------------------------------------
# Address parsing helper
# ---------------------------------------------------------------------------
def _parse_address_header(header_value: Optional[str]) -> list[dict]:
    """
    Parse a comma-separated RFC 2822 address header into a list of
    {"name": ..., "email": ...} dicts.

    Returns an empty list if the header is absent or empty.
    """
    if not header_value:
        return []
    parsed = email.utils.getaddresses([header_value])
    return [{"name": name.strip(), "email": addr.strip()} for name, addr in parsed if addr]


# ---------------------------------------------------------------------------
# .eml parser
# ---------------------------------------------------------------------------
def parse_eml(raw_bytes: bytes) -> ParsedEmail:
    """
    Parse raw .eml bytes and return a ParsedEmail dataclass.

    Raises ValueError if the input cannot be parsed as an email message
    or if the required From header is missing.
    """
    try:
        msg = stdlib_email.message_from_bytes(raw_bytes, policy=email.policy.compat32)
    except Exception as exc:
        raise ValueError(f"Failed to parse .eml content: {exc}") from exc

    sender_raw = msg.get("From", "").strip()
    if not sender_raw:
        raise ValueError("Email is missing required 'From' header.")

    # Extract sender address only (discard display name for the sender column)
    _, sender_addr = email.utils.parseaddr(sender_raw)
    sender = sender_addr if sender_addr else sender_raw

    # Message-ID — strip angle brackets and whitespace
    raw_mid = msg.get("Message-ID", "").strip()
    message_id: Optional[str] = re.sub(r"[\s<>]", "", raw_mid) if raw_mid else None

    # Date → timezone-aware datetime
    received_at: Optional[datetime] = None
    date_str = msg.get("Date", "").strip()
    if date_str:
        try:
            parsed_tuple = email.utils.parsedate_to_datetime(date_str)
            # Ensure UTC if no timezone info provided
            if parsed_tuple.tzinfo is None:
                received_at = parsed_tuple.replace(tzinfo=timezone.utc)
            else:
                received_at = parsed_tuple
        except Exception:
            received_at = None  # Malformed date — store NULL rather than crash

    # Subject — decode RFC 2047 encoded words
    raw_subject = msg.get("Subject", "")
    subject: Optional[str] = stdlib_email.header.decode_header(raw_subject)[0][0] if raw_subject else None
    if isinstance(subject, bytes):
        charset = stdlib_email.header.decode_header(raw_subject)[0][1] or "utf-8"
        subject = subject.decode(charset, errors="replace")

    # Body text — first text/plain part
    body_text: Optional[str] = None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")
                    break
    else:
        if msg.get_content_type() == "text/plain":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")

    # SHA-256 hash of the raw bytes
    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    return ParsedEmail(
        message_id=message_id,
        sender=sender,
        to_recipients=_parse_address_header(msg.get("To")),
        cc_recipients=_parse_address_header(msg.get("Cc")),
        subject=subject,
        body_text=body_text,
        received_at=received_at,
        content_hash=content_hash,
        raw_bytes=raw_bytes,
    )


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------
def _find_duplicate(
    db: Session,
    message_id: Optional[str],
    content_hash: str,
) -> tuple[Optional[Email], Optional[str]]:
    """
    Check for an existing Email row.

    Priority:
      1. Match by message_id (if present) — strongest signal.
      2. Match by content_hash — catches same content with missing/different ID.

    Returns (existing_row, duplicate_reason) or (None, None).
    """
    if message_id:
        existing = db.query(Email).filter(Email.message_id == message_id).first()
        if existing:
            return existing, "message_id"

    existing = db.query(Email).filter(Email.content_hash == content_hash).first()
    if existing:
        return existing, "content_hash"

    return None, None


# ---------------------------------------------------------------------------
# File storage
# ---------------------------------------------------------------------------
def _store_raw_file(raw_bytes: bytes, email_uuid: uuid.UUID) -> str:
    """
    Write the raw .eml bytes to disk under data/emails/ingested/<uuid>.eml.

    Returns the path string stored in the database (relative to project root).
    """
    INGESTED_EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    dest = INGESTED_EMAIL_DIR / f"{email_uuid}.eml"
    dest.write_bytes(raw_bytes)
    # Store a path relative to project root so the record is portable
    return str(dest.relative_to(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Public ingestion entry point
# ---------------------------------------------------------------------------
def ingest_eml(
    raw_bytes: bytes,
    db: Session,
) -> IngestionSuccess | IngestionDuplicate:
    """
    Main ingestion function.

    1. Parse the .eml bytes.
    2. Check for duplicates.
    3. If duplicate → return IngestionDuplicate (no DB write).
    4. If new → store file, create Email row, commit, return IngestionSuccess.

    Raises ValueError for unparseable or invalid input.
    """
    parsed = parse_eml(raw_bytes)

    # Duplicate check
    existing, reason = _find_duplicate(db, parsed.message_id, parsed.content_hash)
    if existing is not None:
        return IngestionDuplicate(
            email_id=existing.email_id,
            message_id=existing.message_id,
            processing_status=existing.processing_status,
            duplicate_reason=reason,  # type: ignore[arg-type]
        )

    # New email — generate UUID now so we can name the file with it
    new_uuid = uuid.uuid4()
    raw_file_path = _store_raw_file(parsed.raw_bytes, new_uuid)

    email_row = Email(
        email_id=new_uuid,
        message_id=parsed.message_id,
        matter_key=None,                        # MUST remain NULL at ingestion
        sender=parsed.sender,
        to_recipients=parsed.to_recipients or None,
        cc_recipients=parsed.cc_recipients or None,
        subject=parsed.subject,
        body_text=parsed.body_text,
        received_at=parsed.received_at,
        raw_file_path=raw_file_path,
        content_hash=parsed.content_hash,
        processing_status=PROCESSING_STATUS_NEW,
    )

    db.add(email_row)
    db.commit()
    db.refresh(email_row)

    return IngestionSuccess(
        email_id=email_row.email_id,
        message_id=email_row.message_id,
        processing_status=email_row.processing_status,
    )
