"""
Law Firm ERP — FastAPI application entry point.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.routes.case_brain import router as case_brain_router
from app.routes.email_detail import router as email_detail_router
from app.routes.matter_assignment import router as matter_assignment_router
from app.routes.matter_detail import router as matter_detail_router
from app.routes.matter_search import router as matter_search_router
from app.routes.review_queue import router as review_queue_router
from app.routes.email_ingestion import router as email_ingestion_router
from app.routes.matter_resolution import router as matter_resolution_router

app = FastAPI(
    title="Law Firm ERP",
    description="Internal ERP backend for a law firm.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(case_brain_router)
app.include_router(review_queue_router)
app.include_router(email_detail_router)
app.include_router(matter_assignment_router)
app.include_router(matter_detail_router)
app.include_router(matter_search_router)
app.include_router(email_ingestion_router)
app.include_router(matter_resolution_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
