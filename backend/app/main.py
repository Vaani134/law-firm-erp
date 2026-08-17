"""
Law Firm ERP — FastAPI application entry point.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.routes.email_ingestion import router as email_ingestion_router

app = FastAPI(
    title="Law Firm ERP",
    description="Internal ERP backend for a law firm.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(email_ingestion_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
