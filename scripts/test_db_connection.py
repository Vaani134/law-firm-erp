"""
Standalone script to verify PostgreSQL connectivity.

Run from the project root:
    python scripts/test_db_connection.py

Expected output on success:
    ✅  status : ok
        detail : Connected to 'law_firm_erp'. Server: PostgreSQL 16.x ...

Expected output on failure:
    ❌  status : error
        detail : <error message>
"""

import sys
from pathlib import Path

# Allow importing from backend/app without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import check_connection  # noqa: E402

if __name__ == "__main__":
    result = check_connection()

    icon = "✅" if result["status"] == "ok" else "❌"
    print(f"\n{icon}  status : {result['status']}")
    print(f"    detail : {result['detail']}\n")

    sys.exit(0 if result["status"] == "ok" else 1)
