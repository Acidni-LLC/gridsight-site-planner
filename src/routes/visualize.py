"""Visualization generation routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.models import VisualizeRequest
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/visualize", tags=["visualize"])


@router.post("")
async def generate_visualization(request: VisualizeRequest) -> Response:
    """Generate a photorealistic visualization of the site plan.

    Uses Gemini Nano Banana (image generation) to create a
    rendered view of the proposed layout overlaid on the
    satellite imagery of the actual parcel.

    Returns PNG image bytes with appropriate content type.
    """
    logger.info(
        "Generating visualization for layout %s, style=%s",
        request.layout_id,
        request.style,
    )

    try:
        gemini = GeminiService()

        image_bytes = await gemini.generate_visualization(
            layout_description=request.layout_description,
            style=request.style or "photorealistic aerial view",
            address=request.address,
        )

        if image_bytes:
            return Response(
                content=image_bytes,
                media_type="image/png",
                headers={
                    "Content-Disposition": (
                        f'inline; filename="site-plan-{request.layout_id}.png"'
                    ),
                    "X-Api-Version": "v20260209-1",
                },
            )

        raise HTTPException(
            status_code=422,
            detail="Visualization generation returned no image data",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Visualization failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Visualization generation failed: {e}"
        ) from e
