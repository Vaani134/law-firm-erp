"""
Application configuration.

Reads settings from environment variables / .env file using pydantic-settings.
No credentials are hardcoded here.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root (.env lives there) regardless of the working
# directory from which Python is launched.
# This file is at:  <project_root>/backend/app/config.py
# So the root is:   config.py → app/ → backend/ → <project_root>
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Top-level settings loaded from the environment."""

    # Full SQLAlchemy-compatible DSN, e.g.
    # postgresql+psycopg://user:password@host:port/dbname
    database_url: str

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        # Ignore extra keys that appear in .env so the app never breaks
        # when new variables are added for other components later.
        extra="ignore",
    )


# Single shared instance — import this everywhere.
settings = Settings()
