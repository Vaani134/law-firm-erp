"""
Seed script — Matter 1 initial Case Brain entries.

Source:
    data/reference/matter_1/Law_Firm_Workflow_Testing_Dataset(Case Brain Log).csv

Imports ONLY rows where Matter_Key == "10001-001".
Idempotent: uses (matter_key, source_reference) as the duplicate-detection key.

Usage (from project root):
    python scripts/seed_case_brain_matter_1.py
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow importing from backend/app without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal
from app.models.case_brain_log import CaseBrainLog
from app.models.matter import Matter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MATTER_KEY = "10001-001"
LOGGED_BY = "seed_case_brain_matter_1"

CSV_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "reference"
    / "matter_1"
    / "Law_Firm_Workflow_Testing_Dataset(Case Brain Log).csv"
)


def parse_event_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD into a timezone-aware datetime (UTC midnight)."""
    dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


def load_csv_rows() -> list[dict]:
    """Read the CSV and return only rows belonging to MATTER_KEY,
    sorted by Brain_Sequence ascending."""
    rows = []
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row["Matter_Key"].strip() == MATTER_KEY:
                rows.append(row)

    # Preserve Brain_Sequence ordering.
    rows.sort(key=lambda r: int(r["Brain_Sequence"]))
    return rows


def run_seed() -> None:
    # ----------------------------------------------------------------
    # Load CSV first so we know what we're working with.
    # ----------------------------------------------------------------
    csv_rows = load_csv_rows()
    print(f"CSV rows found for {MATTER_KEY}: {len(csv_rows)}")

    if not csv_rows:
        print("No rows to import. Exiting.")
        return

    db = SessionLocal()
    try:
        # ----------------------------------------------------------------
        # Guard: matter must exist before inserting Case Brain entries.
        # ----------------------------------------------------------------
        matter = db.get(Matter, MATTER_KEY)
        if matter is None:
            print(f"ERROR — Matter '{MATTER_KEY}' does not exist in the database.")
            print("Run scripts/seed_matter_1.py first, then retry.")
            sys.exit(1)

        # ----------------------------------------------------------------
        # Build a set of source_references already in the DB for this matter.
        # Used for duplicate detection.
        # ----------------------------------------------------------------
        existing_refs: set[str] = {
            ref
            for (ref,) in db.query(CaseBrainLog.source_reference).filter(
                CaseBrainLog.matter_key == MATTER_KEY,
                CaseBrainLog.source_reference.isnot(None),
            )
        }

        inserted = 0
        skipped = 0

        for row in csv_rows:
            source_ref = row["Source_ID"].strip()

            if source_ref in existing_refs:
                skipped += 1
                continue

            entry = CaseBrainLog(
                matter_key=MATTER_KEY,
                email_id=None,                          # Intake entries — no email.
                occurred_at=parse_event_date(row["Event_Date"]),
                source_type=row["Source_Type"].strip(),
                source_reference=source_ref,
                source_actor=None,                      # Not available in source material.
                update_summary=row["Brain_Entry"].strip(),
                logged_by=LOGGED_BY,
            )
            db.add(entry)
            existing_refs.add(source_ref)   # Prevent duplicates within this run.
            inserted += 1

        db.commit()

        print(f"Inserted : {inserted}")
        print(f"Skipped  : {skipped} (already existed)")

        # ----------------------------------------------------------------
        # Final count directly from the DB.
        # ----------------------------------------------------------------
        total = (
            db.query(CaseBrainLog)
            .filter(CaseBrainLog.matter_key == MATTER_KEY)
            .count()
        )
        print(f"Total Case Brain entries for {MATTER_KEY}: {total}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
