"""
Verification script — prints all Case Brain entries for Matter 10001-001.

Usage (from project root):
    python scripts/verify_case_brain_matter_1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal
from app.models.case_brain_log import CaseBrainLog

MATTER_KEY = "10001-001"

db = SessionLocal()
try:
    entries = (
        db.query(CaseBrainLog)
        .filter(CaseBrainLog.matter_key == MATTER_KEY)
        .order_by(CaseBrainLog.occurred_at, CaseBrainLog.brain_entry_id)
        .all()
    )

    if not entries:
        print(f"No Case Brain entries found for matter '{MATTER_KEY}'.")
        sys.exit(1)

    print(f"\nCase Brain entries for matter: {MATTER_KEY}\n")
    print(f"{'─' * 80}")

    for entry in entries:
        print(f"  brain_entry_id   : {entry.brain_entry_id}")
        print(f"  matter_key       : {entry.matter_key}")
        print(f"  occurred_at      : {entry.occurred_at}")
        print(f"  source_type      : {entry.source_type}")
        print(f"  source_reference : {entry.source_reference}")
        print(f"  update_summary   : {entry.update_summary[:120]}...")
        print(f"{'─' * 80}")

    print(f"\nTotal entries: {len(entries)}")
    print("\nVerification passed.\n")

finally:
    db.close()
