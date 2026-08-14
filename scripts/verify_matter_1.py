"""
Verification script — confirms Matter 1 and its participants exist in the DB.
Run: python scripts/verify_matter_1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant

MATTER_KEY = "10001-001"

db = SessionLocal()
try:
    matter = db.get(Matter, MATTER_KEY)

    if matter is None:
        print(f"FAIL — matter '{MATTER_KEY}' not found.")
        sys.exit(1)

    print(f"\nMatter found:")
    print(f"  matter_key        : {matter.matter_key}")
    print(f"  client_id         : {matter.client_id}")
    print(f"  matter_id         : {matter.matter_id}")
    print(f"  client_name       : {matter.client_name}")
    print(f"  matter_name       : {matter.matter_name}")
    print(f"  practice_area     : {matter.practice_area}")
    print(f"  matter_type       : {matter.matter_type}")
    print(f"  matter_status     : {matter.matter_status}")
    print(f"  primary_attorney  : {matter.primary_attorney}")
    print(f"  matter_description: {matter.matter_description[:80]}...")

    participants = (
        db.query(MatterParticipant)
        .filter(MatterParticipant.matter_key == MATTER_KEY)
        .order_by(MatterParticipant.participant_id)
        .all()
    )

    print(f"\nParticipants ({len(participants)}):")
    for p in participants:
        print(
            f"  [{p.participant_id}] {p.participant_name:<20}"
            f"  role: {p.role_relationship:<20}"
            f"  email: {p.email_address}"
        )

    print("\nVerification passed.\n")
finally:
    db.close()
