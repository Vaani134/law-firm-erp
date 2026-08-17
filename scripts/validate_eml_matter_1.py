"""
Validates the 5 synthetic .eml files for Matter 1 against the email plan.

Run: python scripts/validate_eml_matter_1.py
"""

from __future__ import annotations

import csv
import email
import email.policy
import sys
from pathlib import Path

EMAIL_DIR = Path(__file__).parent.parent / "data" / "emails"
PLAN_CSV  = Path(__file__).parent.parent / "data" / "reference" / "matter_1" / "email_plan.csv"

# Load the plan
plan: dict[str, dict] = {}
with PLAN_CSV.open(newline="", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        plan[row["email_id"]] = row

errors   = []
warnings = []

EXPECTED_IDS = ["EMAIL-001", "EMAIL-002", "EMAIL-003", "EMAIL-004", "EMAIL-005"]

for eid in EXPECTED_IDS:
    eml_path = EMAIL_DIR / f"{eid}.eml"

    # File exists?
    if not eml_path.exists():
        errors.append(f"{eid}: file not found at {eml_path}")
        continue

    raw = eml_path.read_bytes()
    msg = email.message_from_bytes(raw, policy=email.policy.compat32)

    p = plan[eid]

    # ── From ──────────────────────────────────────────────────────────
    from_addr = msg.get("From", "")
    if p["from_email"] not in from_addr:
        errors.append(f"{eid}: From should contain '{p['from_email']}', got '{from_addr}'")

    # ── To ────────────────────────────────────────────────────────────
    to_addr = msg.get("To", "")
    if p["to_email"] not in to_addr:
        errors.append(f"{eid}: To should contain '{p['to_email']}', got '{to_addr}'")

    # ── Message-ID present ────────────────────────────────────────────
    mid = msg.get("Message-ID", "")
    if not mid:
        errors.append(f"{eid}: Missing Message-ID header")
    elif eid not in mid:
        warnings.append(f"{eid}: Message-ID '{mid}' does not contain email_id — OK but worth noting")

    # ── Date present ──────────────────────────────────────────────────
    date_hdr = msg.get("Date", "")
    if not date_hdr:
        errors.append(f"{eid}: Missing Date header")
    else:
        # Check the plan year/month/day appear somewhere in the header
        plan_date = p["planned_date"]  # YYYY-MM-DD
        year, month, day = plan_date.split("-")
        if year not in date_hdr:
            errors.append(f"{eid}: Date header '{date_hdr}' does not contain plan year {year}")

    # ── Subject present ───────────────────────────────────────────────
    subject = msg.get("Subject", "")
    if not subject:
        errors.append(f"{eid}: Missing Subject header")

    # ── MIME-Version ──────────────────────────────────────────────────
    if not msg.get("MIME-Version"):
        warnings.append(f"{eid}: Missing MIME-Version header")

    # ── Attachment check ──────────────────────────────────────────────
    attachment_expected = p["attachment_expected"].strip().lower() == "true"
    has_attachment = False
    attachment_names = []

    if msg.is_multipart():
        for part in msg.walk():
            disposition = part.get_content_disposition() or ""
            if "attachment" in disposition:
                has_attachment = True
                fn = part.get_filename() or ""
                attachment_names.append(fn)

    if attachment_expected and not has_attachment:
        errors.append(f"{eid}: Attachment expected but none found in MIME structure")
    if not attachment_expected and has_attachment:
        errors.append(f"{eid}: No attachment expected but found: {attachment_names}")

    # ── Body non-empty ────────────────────────────────────────────────
    body_found = False
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload and len(payload.strip()) > 50:
                    body_found = True
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload and len(payload.strip()) > 50:
            body_found = True

    if not body_found:
        errors.append(f"{eid}: text/plain body missing or too short")

    # ── Summary for this file ─────────────────────────────────────────
    attach_str = f"attachment: {attachment_names}" if has_attachment else "no attachment"
    print(f"  {eid}  From: {from_addr}  |  {attach_str}")

# ── Message-ID uniqueness ─────────────────────────────────────────────────────
all_mids = []
for eid in EXPECTED_IDS:
    eml_path = EMAIL_DIR / f"{eid}.eml"
    if eml_path.exists():
        msg = email.message_from_bytes(eml_path.read_bytes(), policy=email.policy.compat32)
        all_mids.append(msg.get("Message-ID", ""))

if len(all_mids) != len(set(all_mids)):
    errors.append("Duplicate Message-IDs detected across files")

# ── Final report ──────────────────────────────────────────────────────────────
print(f"\n{'─'*60}")
if errors:
    print(f"ERRORS ({len(errors)}):")
    for e in errors:
        print(f"  ✗ {e}")
else:
    print("  ✓ No errors.")

if warnings:
    print(f"\nWARNINGS ({len(warnings)}):")
    for w in warnings:
        print(f"  ⚠ {w}")

print(f"\nFiles checked : {len(EXPECTED_IDS)}")
print(f"Errors        : {len(errors)}")
print(f"Warnings      : {len(warnings)}")

if errors:
    sys.exit(1)
else:
    print("\nValidation passed.\n")
