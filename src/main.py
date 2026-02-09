"""GridSight SitePlanner - FastAPI Application.

AI-powered site planning and energy estimation service using
Google Gemini, Maps, and Solar APIs.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.routes import energy, health, layouts, parcels, visualize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

APP_VERSION = "v20260209-1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info(
        "🚀 GridSight SitePlanner starting — port %d, version %s",
        settings.port,
        APP_VERSION,
    )
    logger.info("Gemini API: %s", "configured" if settings.gemini_api_key else "NOT SET")
    logger.info("Solar API: %s", "configured" if settings.solar_api_key else "NOT SET")
    logger.info("Maps API: %s", "configured" if settings.maps_api_key else "NOT SET")

    yield

    logger.info("GridSight SitePlanner shutting down")


app = FastAPI(
    title="GridSight SitePlanner",
    description=(
        "AI-powered site planning and energy estimation. Analyze parcels of land, "
        "lay out structures (homes, garages, sheds, fences, gardens), and estimate "
        "monthly/yearly energy usage with solar potential analysis."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow GridSight frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gridsight.acidni.net",
        "https://gridsight-dev.acidni.net",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(health.router)
app.include_router(parcels.router)
app.include_router(layouts.router)
app.include_router(energy.router)
app.include_router(visualize.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:  # noqa: ANN001, ARG001
    """Catch-all exception handler with structured logging."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "version": APP_VERSION,
        },
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
