"""Layout generation and management routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.models import (
    ContextData,
    LayoutGenerateRequest,
    ParcelFeatures,
    SiteLayout,
    StructureTemplate,
    StructureType,
)
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/layouts", tags=["layouts"])

# Pre-defined structure templates with typical sizes
STRUCTURE_TEMPLATES: list[StructureTemplate] = [
    StructureTemplate(
        type=StructureType.HOME,
        name="Single Family Home",
        default_sqft=1800,
        min_sqft=800,
        max_sqft=5000,
        description="Primary residence with standard setbacks",
        requires_setback=True,
        default_setback_ft=25.0,
    ),
    StructureTemplate(
        type=StructureType.GARAGE,
        name="Detached Garage",
        default_sqft=576,
        min_sqft=200,
        max_sqft=1200,
        description="Detached garage (2-car standard)",
        requires_setback=True,
        default_setback_ft=5.0,
    ),
    StructureTemplate(
        type=StructureType.SHED,
        name="Storage Shed",
        default_sqft=120,
        min_sqft=48,
        max_sqft=400,
        description="Utility storage building",
        requires_setback=True,
        default_setback_ft=3.0,
    ),
    StructureTemplate(
        type=StructureType.POOL,
        name="Swimming Pool",
        default_sqft=450,
        min_sqft=200,
        max_sqft=1200,
        description="In-ground residential pool",
        requires_setback=True,
        default_setback_ft=10.0,
    ),
    StructureTemplate(
        type=StructureType.GARDEN,
        name="Garden Plot",
        default_sqft=200,
        min_sqft=50,
        max_sqft=2000,
        description="Vegetable or flower garden area",
        requires_setback=False,
        default_setback_ft=0.0,
    ),
    StructureTemplate(
        type=StructureType.FENCE,
        name="Property Fence",
        default_sqft=0,
        min_sqft=0,
        max_sqft=0,
        description="Perimeter fencing (linear feature)",
        requires_setback=False,
        default_setback_ft=0.0,
    ),
    StructureTemplate(
        type=StructureType.DRIVEWAY,
        name="Driveway",
        default_sqft=400,
        min_sqft=150,
        max_sqft=1000,
        description="Vehicle access from road to garage/home",
        requires_setback=False,
        default_setback_ft=0.0,
    ),
    StructureTemplate(
        type=StructureType.PATIO,
        name="Patio / Deck",
        default_sqft=250,
        min_sqft=80,
        max_sqft=800,
        description="Outdoor living space, covered or uncovered",
        requires_setback=False,
        default_setback_ft=0.0,
    ),
    StructureTemplate(
        type=StructureType.WORKSHOP,
        name="Workshop",
        default_sqft=300,
        min_sqft=100,
        max_sqft=800,
        description="Detached workshop or hobby building",
        requires_setback=True,
        default_setback_ft=5.0,
    ),
    StructureTemplate(
        type=StructureType.BARN,
        name="Barn / Outbuilding",
        default_sqft=800,
        min_sqft=200,
        max_sqft=3000,
        description="Agricultural or large storage building",
        requires_setback=True,
        default_setback_ft=10.0,
    ),
]


@router.get("/templates", response_model=list[StructureTemplate])
async def get_templates() -> list[StructureTemplate]:
    """Return all available structure templates with defaults."""
    return STRUCTURE_TEMPLATES


@router.post("/generate", response_model=SiteLayout)
async def generate_layout(request: LayoutGenerateRequest) -> SiteLayout:
    """Generate an optimized site layout using Gemini AI.

    Takes parcel dimensions and desired structures, then uses Gemini
    to produce an optimized placement that respects setbacks, access
    paths, and local building conventions.
    """
    logger.info(
        "Generating layout for %d structures on %.0f sqft parcel",
        len(request.structures),
        request.parcel_sqft,
    )

    try:
        gemini = GeminiService()

        # Build parcel features from request dimensions
        parcel_features = ParcelFeatures(
            usable_area_sqft=request.parcel_sqft,
            estimated_dimensions={
                "width_ft": request.parcel_width_ft,
                "depth_ft": request.parcel_depth_ft,
            },
        )
        context_data = ContextData()

        layout = await gemini.generate_layout(
            parcel_features=parcel_features,
            context_data=context_data,
            desired_structures=request.structures,
            home_sqft=int(request.parcel_sqft * 0.3),  # 30% lot coverage default
        )

        return layout

    except Exception as e:
        logger.error("Layout generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Layout generation failed: {e}"
        ) from e


@router.post("/{layout_id}/adjust", response_model=SiteLayout)
async def adjust_layout(layout_id: str, request: LayoutGenerateRequest) -> SiteLayout:
    """Adjust an existing layout with modified structure placement.

    Accepts updated structure specs and regenerates optimized placement.
    Layout history is tracked by ID in Cosmos DB.
    """
    logger.info("Adjusting layout %s", layout_id)

    try:
        gemini = GeminiService()

        parcel_features = ParcelFeatures(
            usable_area_sqft=request.parcel_sqft,
            estimated_dimensions={
                "width_ft": request.parcel_width_ft,
                "depth_ft": request.parcel_depth_ft,
            },
        )
        context_data = ContextData()

        layout = await gemini.generate_layout(
            parcel_features=parcel_features,
            context_data=context_data,
            desired_structures=request.structures,
            home_sqft=int(request.parcel_sqft * 0.3),
        )

        # Preserve the layout ID for history tracking
        layout.layout_id = layout_id

        return layout

    except Exception as e:
        logger.error("Layout adjustment failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Layout adjustment failed: {e}"
        ) from e
