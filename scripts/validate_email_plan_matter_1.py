"""
Validation script — verifies email_plan.csv for Matter 1.
Run: python scripts/validate_email_plan_matter_1.py
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

CSV_PATH = (
    Path(__file__).parent.parent
    / "data" / "reference" / "matter_1" / "email_plan.csv"
)

REQUIRED_COLUMNS = {
    "email_id", "sequence", "planned_date", "from_name", "from_email",
    "to_name", "to_email", "cc", "subject", "communication_type",
    "business_event", "expected_matter_key", "attachment_expected",
    "attachment_description", "expected_case_brain_impact",
}

KNOWN_EMAILS = {
    "maya.desai@harborspirits.example",
    "kevin.russo@riversideliquors.example",
    "abell@bellmercer.example",
    "spatel@samplelaw.example",
}

errors = []

with CSV_PATH.open(newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    columns = set(reader.fieldnames or [])
    missing_cols = REQUIRED_COLUMNS - columns
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    rows = list(reader)

# Row count
if len(rows) != 5:
    errors.append(f"Expected 5 rows, found {len(rows)}")

# Uniqueness of email_id
ids = [r["email_id"] for r in rows]
if len(ids) != len(set(ids)):
    errors.append(f"Duplicate email_ids: {ids}")

# Expected IDs
expected_ids = {"EMAIL-001", "EMAIL-002", "EMAIL-003", "EMAIL-004", "EMAIL-005"}
if set(ids) != expected_ids:
    errors.append(f"email_id set mismatch. Found: {set(ids)}")

# All matter keys = 10001-001
bad_keys = [r["email_id"] for r in rows if r["expected_matter_key"] != "10001-001"]
if bad_keys:
    errors.append(f"Wrong expected_matter_key in: {bad_keys}")

# Dates are chronological
dates = []
for r in rows:
    try:
        dates.append((r["email_id"], date.fromisoformat(r["planned_date"])))
    except ValueError:
        errors.append(f"{r['email_id']}: invalid date '{r['planned_date']}'")

for i in range(1, len(dates)):
    if dates[i][1] < dates[i - 1][1]:
        errors.append(
            f"Date out of order: {dates[i][0]} ({dates[i][1]}) "
            f"before {dates[i-1][0]} ({dates[i-1][1]})"
        )

# from/to emails are known participants (warn, not error, for realism)
warnings = []
for r in rows:
    for field in ("from_email", "to_email"):
        addr = r[field].strip()
        if addr and addr not in KNOWN_EMAILS:
            warnings.append(f"{r['email_id']} {field} '{addr}' not in known participant list")

# attachment_expected consistency
for r in rows:
    ae = r["attachment_expected"].strip().lower()
    if ae not in ("true", "false"):
        errors.append(f"{r['email_id']}: attachment_expected must be true/false, got '{ae}'")
    if ae == "true" and not r["attachment_description"].strip():
        errors.append(f"{r['email_id']}: attachment_expected=true but description is empty")
    if ae == "false" and r["attachment_description"].strip():
        errors.append(f"{r['email_id']}: attachment_expected=false but description is non-empty")

# Case Brain impact non-trivial (warn if too short)
for r in rows:
    impact = r["expected_case_brain_impact"].strip()
    if len(impact) < 20:
        warnings.append(f"{r['email_id']}: expected_case_brain_impact may be too brief: '{impact}'")

# ── Report ────────────────────────────────────────────────────────────────────
print(f"\nValidating: {CSV_PATH.name}\n{'─'*60}")

if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  ✗ {e}")
else:
    print("  ✓ No errors found.")

if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(f"  ⚠ {w}")

print(f"\nRows validated: {len(rows)}")
print(f"Errors: {len(errors)}  |  Warnings: {len(warnings)}")

if errors:
    sys.exit(1)
else:
    print("\nValidation passed.\n")
