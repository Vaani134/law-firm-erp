"""
Validates the 5 synthetic .eml files for Matter 1.

Checks:
  1.  Exactly 5 .eml files exist in data/emails/matter_1/
  2.  Every .eml parses without error via Python's email library.
  3.  Every .eml has: From, To, Subject, Date, Message-ID
  4.  Message-ID values are unique across all 5 files.
  5.  Sender/recipient addresses belong to known Matter 1 participants.
  6.  EMAIL-003 contains an attachment (premises lease).
  7.  EMAIL-005 contains an attachment (asset list).
  8.  No unexpected 6th .eml exists.
  9.  Sequence matches email_plan.csv (from/to/date).
  10. Attachment files exist in data/attachments/matter_1/

Run: python scripts/validate_matter_1_emails.py
"""

from __future__ import annotations

import csv
import email
import email.policy
import sys
from pathlib import Path

ROOT         = Path(__file__).parent.parent
EMAIL_DIR    = ROOT / "data" / "emails" / "matter_1"
ATTACH_DIR   = ROOT / "data" / "attachments" / "matter_1"
PLAN_CSV     = ROOT / "data" / "reference" / "matter_1" / "email_plan.csv"

EXPECTED_IDS = ["EMAIL-001", "EMAIL-002", "EMAIL-003", "EMAIL-004", "EMAIL-005"]

KNOWN_PARTICIPANTS = {
    "maya.desai@harborspirits.example",
    "kevin.russo@riversideliquors.example",
    "abell@bellmercer.example",
    "spatel@samplelaw.example",
}

EXPECTED_ATTACHMENTS = {
    "EMAIL-003": "existing_premises_lease.pdf",
    "EMAIL-005": "preliminary_asset_list.pdf",
}

errors   = []
warnings = []

# ── 1. Load email plan ────────────────────────────────────────────────────────
plan: dict[str, dict] = {}
with PLAN_CSV.open(newline="", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        plan[row["email_id"]] = row

# ── 2. Check exactly 5 files, no unexpected 6th ───────────────────────────────
eml_files = sorted(EMAIL_DIR.glob("*.eml"))
found_ids  = [f.stem for f in eml_files]

if len(eml_files) != 5:
    errors.append(f"Expected 5 .eml files, found {len(eml_files)}: {found_ids}")

unexpected = set(found_ids) - set(EXPECTED_IDS)
if unexpected:
    errors.append(f"Unexpected .eml files found: {unexpected}")

# ── 3. Attachment files exist ─────────────────────────────────────────────────
for eid, fname in EXPECTED_ATTACHMENTS.items():
    att_path = ATTACH_DIR / fname
    if not att_path.exists():
        errors.append(f"Attachment file missing: {att_path}")
    else:
        size = att_path.stat().st_size
        if size < 100:
            errors.append(f"Attachment {fname} is suspiciously small ({size} bytes)")

# ── 4. Parse and validate each .eml ──────────────────────────────────────────
all_message_ids = []
print(f"\nValidating .eml files in: {EMAIL_DIR}\n{'─'*70}")

for eid in EXPECTED_IDS:
    eml_path = EMAIL_DIR / f"{eid}.eml"
    if not eml_path.exists():
        errors.append(f"{eid}: file not found")
        print(f"  {eid}  MISSING")
        continue

    raw = eml_path.read_bytes()
    try:
        msg = email.message_from_bytes(raw, policy=email.policy.compat32)
    except Exception as exc:
        errors.append(f"{eid}: parse error — {exc}")
        print(f"  {eid}  PARSE ERROR: {exc}")
        continue

    p = plan.get(eid, {})

    # Required headers
    for hdr in ("From", "To", "Subject", "Date", "Message-ID"):
        if not msg.get(hdr, "").strip():
            errors.append(f"{eid}: missing header '{hdr}'")

    # Message-ID uniqueness tracking
    mid = msg.get("Message-ID", "").strip()
    all_message_ids.append((eid, mid))

    # From/To match plan
    from_addr = msg.get("From", "")
    to_addr   = msg.get("To", "")
    if p.get("from_email") and p["from_email"] not in from_addr:
        errors.append(f"{eid}: From '{from_addr}' does not match plan '{p['from_email']}'")
    if p.get("to_email") and p["to_email"] not in to_addr:
        errors.append(f"{eid}: To '{to_addr}' does not match plan '{p['to_email']}'")

    # Addresses are known participants
    for addr_hdr in ("From", "To"):
        val = msg.get(addr_hdr, "")
        matched = any(known in val for known in KNOWN_PARTICIPANTS)
        if not matched:
            errors.append(f"{eid}: {addr_hdr} '{val}' is not a known Matter 1 participant")

    # Date contains plan year
    date_hdr = msg.get("Date", "")
    if p.get("planned_date") and p["planned_date"][:4] not in date_hdr:
        errors.append(f"{eid}: Date '{date_hdr}' does not contain plan year")

    # Attachment check
    attachment_expected = p.get("attachment_expected", "false").lower() == "true"
    found_attachments   = []
    if msg.is_multipart():
        for part in msg.walk():
            disp = part.get_content_disposition() or ""
            if "attachment" in disp:
                found_attachments.append(part.get_filename() or "unnamed")

    if attachment_expected and not found_attachments:
        errors.append(f"{eid}: attachment expected per plan but none found in MIME structure")
    if not attachment_expected and found_attachments:
        errors.append(f"{eid}: no attachment expected per plan but found: {found_attachments}")

    # Attachment filename matches expected
    if eid in EXPECTED_ATTACHMENTS:
        expected_fname = EXPECTED_ATTACHMENTS[eid]
        if not any(expected_fname in fn for fn in found_attachments):
            errors.append(
                f"{eid}: expected attachment filename '{expected_fname}', "
                f"found: {found_attachments}"
            )

    # Body non-empty
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_text = payload.decode("utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_text = payload.decode("utf-8", errors="replace")

    if len(body_text.strip()) < 50:
        errors.append(f"{eid}: text/plain body is missing or too short")

    attach_str = f"attachment: {found_attachments}" if found_attachments else "no attachment"
    print(f"  {eid}  From: {from_addr}")
    print(f"         To  : {to_addr}")
    print(f"         Date: {date_hdr}")
    print(f"         {attach_str}")

# ── 5. Message-ID uniqueness ──────────────────────────────────────────────────
mid_values = [m for _, m in all_message_ids]
if len(mid_values) != len(set(mid_values)):
    dupes = [m for m in mid_values if mid_values.count(m) > 1]
    errors.append(f"Duplicate Message-IDs: {set(dupes)}")

# ── Final report ──────────────────────────────────────────────────────────────
print(f"\n{'─'*70}")
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

print(f"\nFiles checked  : {len(EXPECTED_IDS)}")
print(f"Errors         : {len(errors)}")
print(f"Warnings       : {len(warnings)}")

if errors:
    sys.exit(1)
else:
    print("\nValidation passed.\n")
