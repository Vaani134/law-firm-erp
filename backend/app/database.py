"""
Database connectivity layer.

Provides:
  - engine         : SQLAlchemy async-capable engine (sync here for simplicity)
  - SessionLocal   : session factory bound to the engine
  - Base           : declarative base — all ORM models will inherit from this
  - get_db()       : FastAPI dependency that yields a database session
  - check_connection(): lightweight connectivity test
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# pool_pre_ping=True makes SQLAlchemy test each connection from the pool
# before using it, automatically reconnecting on stale connections.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # Keep the pool small until real workload is known.
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set to True to log every SQL statement (useful for debugging).
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
# autocommit=False  → transactions must be committed explicitly
# autoflush=False   → changes are not flushed to DB before every query
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
# All ORM models will inherit from Base.
# Example (do NOT add here — put in models/):
#   class Matter(Base):
#       __tablename__ = "matters"
#       ...
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy session for the duration of a single request,
    then close it automatically.

    Usage in a route:
        from fastapi import Depends
        from app.database import get_db

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Connectivity test (no ORM models required)
# ---------------------------------------------------------------------------
def check_connection() -> dict:
    """
    Execute a trivial SQL statement to verify the database is reachable.

    Returns a dict:
        {"status": "ok",    "detail": "Connected to law_firm_erp ..."}
        {"status": "error", "detail": "<error message>"}
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database(), version()"))
            db_name, version = result.one()
        return {
            "status": "ok",
            "detail": f"Connected to '{db_name}'. Server: {version}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}
