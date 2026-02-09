"""Parcel analysis routes."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.models import (
    ParcelAnalyzeRequest,
    ProjectResponse,
    ProjectStatus,
)
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/parcels", tags=["parcels"])


@router.post("/analyze", response_model=ProjectResponse)
async def analyze_parcel(request: ParcelAnalyzeRequest) -> ProjectResponse:
    """Analyze a parcel of land using satellite imagery and Gemini AI.

    Steps:
    1. Fetch satellite imagery from Google Maps Static API
    2. Analyze image with Gemini 2.5 Flash (object detection, boundaries)
    3. Get location context via Gemini Maps Grounding (zoning, climate)
    4. Return parcel analysis with features and context
    """
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    logger.info("Starting parcel analysis: %s -> %s", request.address, project_id)

    try:
        gemini = GeminiService()

        # Get coordinates (use provided or geocode would go here)
        lat = request.lat or 29.7147  # Default to Hastings FL
        lng = request.lng or -81.5036

        # Step 1: Get satellite image
        satellite_image = await gemini.get_satellite_image(lat, lng, zoom=20)
        logger.info("Satellite image acquired: %d bytes", len(satellite_image))

        # Step 2 & 3: Analyze parcel with Gemini
        analysis = await gemini.analyze_parcel(
            satellite_image=satellite_image,
            address=request.address,
            lat=lat,
            lng=lng,
        )

        return ProjectResponse(
            id=project_id,
            name=f"Site Plan - {request.address}",
            address=request.address,
            lat=lat,
            lng=lng,
            status=ProjectStatus.ANALYZING,
            parcel_analysis=analysis,
        )

    except Exception as e:
        logger.error("Parcel analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Parcel analysis failed: {e}") from e
