"""Health check route."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter

from src.models import HealthResponse

router = APIRouter(tags=["health"])

APP_VERSION = "v20260209-1"
APP_NAME = "gridsight-site-planner"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status with version info."""
    return HealthResponse(
        status="healthy",
        service=APP_NAME,
        version=APP_VERSION,
        timestamp=dt.datetime.now(dt.UTC).isoformat(),
    )
