"""
Seed script — Matter 1: Harbor Spirits / Riverside Liquors Acquisition

Source material:
  data/reference/matter_1/Matter_1_Testing_Data_Preparation_Instructions.pdf
  data/reference/matter_1/Law_Firm_Workflow_Testing_Dataset(Case Brain Log).csv

Safe to run repeatedly — will not create duplicate records.

Usage (from project root):
    python scripts/seed_matter_1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing from backend/app without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal
from app.models.matter import Matter
from app.models.matter_participant import MatterParticipant

# ---------------------------------------------------------------------------
# Seed data — sourced entirely from the Matter 1 reference material.
# ---------------------------------------------------------------------------

MATTER_KEY = "10001-001"

MATTER_DATA = {
    "matter_key": MATTER_KEY,
    "client_id": "10001",
    "matter_id": "001",
    "client_name": "Harbor Spirits Holdings LLC",
    "matter_name": "Harbor Spirits / Riverside Liquors Acquisition",
    "practice_area": "Corporate",
    "matter_type": "M&A - Asset Purchase",
    "matter_description": (
        "Representation of Harbor Spirits Holdings LLC in the purchase of "
        "substantially all assets of Riverside Liquors, an operating retail "
        "liquor store in Montclair, New Jersey. The store operates from leased "
        "premises. Transaction is structured as an asset purchase. Discussed "
        "purchase price approximately $1.15 million. Scope includes furniture, "
        "fixtures, equipment, trade name, goodwill and certain inventory. "
        "Premises lease assignment and liquor-license transfer must be addressed."
    ),
    "matter_aliases_identifiers": (
        "Harbor Spirits; Riverside Liquors; Riverside Liquors LLC; "
        "10001-001; Harbor Spirits Acquisition; Liquor Store Asset Purchase; "
        "Montclair NJ liquor store"
    ),
    "matter_status": "open",
    "primary_attorney": "Sarah Patel",
}

# Each entry maps to one matter_participants row.
# Source: Matter_1_Testing_Data_Preparation_Instructions.pdf — Section 2.
PARTICIPANTS = [
    {
        "participant_name": "Maya Desai",
        "email_address": "maya.desai@harborspirits.example",
        "organization": "Harbor Spirits Holdings LLC",
        "role_relationship": "client",
        "is_active": True,
    },
    {
        "participant_name": "Kevin Russo",
        "email_address": "kevin.russo@riversideliquors.example",
        "organization": "Riverside Liquors LLC",
        "role_relationship": "seller",
        "is_active": True,
    },
    {
        "participant_name": "Anthony Bell",
        "email_address": "abell@bellmercer.example",
        "organization": "Bell & Mercer LLP",
        "role_relationship": "opposing_counsel",
        "is_active": True,
    },
    {
        "participant_name": "Sarah Patel",
        "email_address": "spatel@samplelaw.example",
        "organization": "Sample Law Firm",
        "role_relationship": "primary_attorney",
        "is_active": True,
    },
]


def run_seed() -> None:
    db = SessionLocal()
    try:
        existing_matter = db.get(Matter, MATTER_KEY)

        if existing_matter is not None:
            print(f"Matter {MATTER_KEY} already exists.")
            print("No duplicate records created.")
            return

        # ----------------------------------------------------------------
        # Create the Matter
        # ----------------------------------------------------------------
        matter = Matter(**MATTER_DATA)
        db.add(matter)
        db.flush()  # Assign PK before inserting participants (FK constraint).

        # ----------------------------------------------------------------
        # Create participants
        # ----------------------------------------------------------------
        participant_objects = []
        for p in PARTICIPANTS:
            participant = MatterParticipant(matter_key=MATTER_KEY, **p)
            db.add(participant)
            participant_objects.append(participant)

        db.commit()

        print(f"Matter {MATTER_KEY} created.")
        print(f"Participants created: {len(participant_objects)}")
        for p in participant_objects:
            print(f"  - {p.participant_name} ({p.role_relationship})")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
