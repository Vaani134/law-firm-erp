"""
Verify email ingestion results.

Queries the emails table for the most recently ingested records, displays
key fields, and confirms the raw .eml file referenced by raw_file_path exists
on disk.

Usage (from project root):
    python scripts/verify_email_ingestion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing from backend/app without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal
from app.models.email import Email

# raw_file_path is stored relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# How many recent rows to show
_SHOW_LAST = 10


def run() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(Email)
            .order_by(Email.created_at.desc())
            .limit(_SHOW_LAST)
            .all()
        )
    finally:
        db.close()

    if not rows:
        print("\nNo emails found in the database.\n")
        sys.exit(1)

    print(f"\nMost recently ingested emails ({len(rows)} shown)\n")
    print("=" * 80)

    all_files_ok = True

    for row in rows:
        # Resolve raw_file_path — stored as relative path from project root
        file_path = _PROJECT_ROOT / row.raw_file_path
        file_exists = file_path.exists()
        if not file_exists:
            all_files_ok = False

        file_status = "EXISTS" if file_exists else "MISSING ✗"

        print(f"  email_id          : {row.email_id}")
        print(f"  message_id        : {row.message_id}")
        print(f"  matter_key        : {row.matter_key}")
        print(f"  sender            : {row.sender}")
        print(f"  subject           : {row.subject!r:.70}")
        print(f"  received_at       : {row.received_at}")
        print(f"  processing_status : {row.processing_status}")
        print(f"  content_hash      : {row.content_hash}")
        print(f"  raw_file_path     : {row.raw_file_path}")
        print(f"  file on disk      : {file_status}")
        print("-" * 80)

    print(f"\nDatabase records : {len(rows)}")
    print(f"Files present    : {sum(1 for r in rows if (_PROJECT_ROOT / r.raw_file_path).exists())}/{len(rows)}")

    if all_files_ok:
        print("\nVerification passed.\n")
    else:
        print("\nVerification FAILED — one or more raw .eml files are missing.\n")
        sys.exit(1)


if __name__ == "__main__":
    run()
