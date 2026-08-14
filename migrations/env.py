"""
Alembic environment configuration.

Key decisions:
  - DATABASE_URL is read from the .env file via app.config.settings.
    No credentials are ever hardcoded.
  - app.models is imported so Alembic autogenerate can compare ORM
    metadata against the live database schema.
  - Only synchronous (offline + online) migration modes are implemented;
    the connection layer is synchronous SQLAlchemy 2.x.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Make sure `app` is importable when Alembic runs from the project root.
# Project layout:  <root>/backend/app/...
#                  <root>/migrations/env.py   ← this file
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Import settings FIRST (reads DATABASE_URL from .env)
# ---------------------------------------------------------------------------
from app.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Import ALL models so Alembic autogenerate sees them.
# app/models/__init__.py re-exports every model class.
# ---------------------------------------------------------------------------
import app.models  # noqa: F401 E402
from app.database import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic boilerplate
# ---------------------------------------------------------------------------
config = context.config

# Inject DATABASE_URL from .env — overrides any value in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object Alembic compares against the database.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode (generates SQL without a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Keep timezone-aware TIMESTAMP columns rendered correctly.
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (connects to the live database)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
