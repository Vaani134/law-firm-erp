"""
Quick schema verification — lists tables and their columns in law_firm_erp.
Run: python scripts/verify_schema.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, inspect, text
from app.config import settings

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    # Confirm Alembic migration version
    try:
        rev = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        print(f"\nAlembic revision: {rev}")
    except Exception:
        print("\nAlembic version table not found")

    insp = inspect(engine)
    tables = sorted(insp.get_table_names(schema="public"))
    # Exclude the alembic version table from display
    data_tables = [t for t in tables if t != "alembic_version"]

    print(f"\nData tables ({len(data_tables)}):")
    for table in data_tables:
        cols = insp.get_columns(table, schema="public")
        indexes = insp.get_indexes(table, schema="public")
        fks = insp.get_foreign_keys(table, schema="public")
        print(f"\n  {table}")
        print("    columns:")
        for c in cols:
            nullable = "NULL" if c["nullable"] else "NOT NULL"
            print(f"      {c['name']:<35} {str(c['type']):<30} {nullable}")
        if fks:
            print("    foreign keys:")
            for fk in fks:
                print(f"      {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
        if indexes:
            print("    indexes:")
            for ix in indexes:
                print(f"      {ix['name']}")

print("\nDone.\n")
