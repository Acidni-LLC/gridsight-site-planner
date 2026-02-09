"""Health check route."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter

from src.config import get_settings
from src.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status with version info."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=dt.datetime.now(dt.UTC).isoformat(),
    )
