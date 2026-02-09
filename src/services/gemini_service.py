"""Gemini AI service for parcel analysis, layout generation, and visualization."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from google import genai
from google.genai import types

from src.config import get_settings
from src.models import (
    ContextData,
    DetectedStructure,
    ParcelAnalysisResult,
    ParcelFeatures,
    PlacedStructure,
    SiteLayout,
    StructureType,
)

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for Google Gemini AI interactions."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.google_gemini_api_key
        self.client = genai.Client(api_key=self.api_key)
        self.maps_api_key = settings.google_maps_api_key

    async def get_satellite_image(
        self, lat: float, lng: float, zoom: int = 20, size: str = "640x640"
    ) -> bytes:
        """Fetch satellite imagery from Google Maps Static API."""
        url = "https://maps.googleapis.com/maps/api/staticmap"
        params = {
            "center": f"{lat},{lng}",
            "zoom": zoom,
            "size": size,
            "maptype": "satellite",
            "key": self.maps_api_key,
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.content

    async def analyze_parcel(
        self,
        satellite_image: bytes,
        address: str,
        lat: float,
        lng: float,
    ) -> ParcelAnalysisResult:
        """Analyze a parcel using Gemini 2.5 Flash Image Understanding."""
        logger.info("Analyzing parcel at %s (%.4f, %.4f)", address, lat, lng)

        # Step 1: Image analysis with Gemini Vision
        image_part = types.Part.from_bytes(data=satellite_image, mime_type="image/png")

        analysis_prompt = """Analyze this satellite image of a residential parcel.
Return a JSON object with these fields:
{
  "parcel_boundary": [[y1,x1], [y2,x2], ...],  // polygon coords normalized 0-1000
  "existing_structures": [
    {"type": "house|shed|pool|driveway|other", "bbox": {"y_min": 0, "x_min": 0, "y_max": 0, "x_max": 0}, "area_estimate_sqft": 0, "confidence": 0.0}
  ],
  "vegetation_areas": [
    {"type": "trees|lawn|garden", "bbox": {"y_min": 0, "x_min": 0, "y_max": 0, "x_max": 0}}
  ],
  "access_points": [
    {"type": "driveway|road_frontage", "location": "north|south|east|west"}
  ],
  "orientation_deg": 0,
  "usable_area_sqft": 0,
  "estimated_dimensions": {"width_ft": 0, "depth_ft": 0},
  "setback_estimate": {"front_ft": 25, "side_ft": 10, "rear_ft": 20}
}

Be precise with bounding boxes. If you cannot determine a value, use reasonable defaults for a Florida residential lot."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image_part, analysis_prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )

            # Parse the JSON response
            analysis_data = json.loads(response.text)
            logger.info("Parcel analysis complete: %d structures detected",
                        len(analysis_data.get("existing_structures", [])))

            # Build ParcelFeatures from response
            existing_structures = [
                DetectedStructure(**s) for s in analysis_data.get("existing_structures", [])
            ]

            parcel_features = ParcelFeatures(
                parcel_boundary=analysis_data.get("parcel_boundary", []),
                existing_structures=existing_structures,
                vegetation_areas=analysis_data.get("vegetation_areas", []),
                access_points=analysis_data.get("access_points", []),
                orientation_deg=analysis_data.get("orientation_deg", 0),
                usable_area_sqft=analysis_data.get("usable_area_sqft", 0),
                estimated_dimensions=analysis_data.get("estimated_dimensions", {}),
                setback_estimate=analysis_data.get(
                    "setback_estimate", {"front_ft": 25, "side_ft": 10, "rear_ft": 20}
                ),
            )

        except Exception as e:
            logger.error("Gemini image analysis failed: %s", e)
            # Return reasonable defaults so the pipeline continues
            parcel_features = ParcelFeatures(
                usable_area_sqft=10000,
                estimated_dimensions={"width_ft": 100, "depth_ft": 100},
            )

        # Step 2: Context data from Maps Grounding
        context_data = await self._get_maps_context(address, lat, lng)

        return ParcelAnalysisResult(
            parcel_features=parcel_features,
            context_data=context_data,
        )

    async def _get_maps_context(
        self, address: str, lat: float, lng: float
    ) -> ContextData:
        """Get location-aware context using Gemini Maps Grounding."""
        context_prompt = f"""For the property at {address} (lat: {lat}, lng: {lng}):
Return a JSON object with:
{{
  "zoning": "residential single-family / residential multi-family / agricultural / etc",
  "climate_zone": "IECC zone (e.g., 2A)",
  "avg_temp_high_f": 0,
  "avg_temp_low_f": 0,
  "prevailing_wind": "direction (e.g., SE)",
  "soil_type": "sand / clay / loam / etc",
  "flood_zone": "X / A / AE / VE / etc",
  "nearby_utilities": ["electric", "water", "sewer", "natural_gas"]
}}

Use your knowledge of this location. Be specific to this address."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=context_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_maps=types.GoogleMaps())],
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            context = json.loads(response.text)
            return ContextData(**context)
        except Exception as e:
            logger.warning("Maps grounding failed, using defaults: %s", e)
            return ContextData(
                zoning="residential single-family",
                climate_zone="2A",
                avg_temp_high_f=82,
                avg_temp_low_f=58,
                prevailing_wind="SE",
                soil_type="sandy loam",
                flood_zone="X",
                nearby_utilities=["electric", "water"],
            )

    async def generate_layout(
        self,
        parcel_features: ParcelFeatures,
        context_data: ContextData,
        desired_structures: list[StructureType],
        home_sqft: int,
        garage_cars: int = 2,
        shed_sqft: int = 120,
        garden_sqft: int = 200,
        fence_type: str = "privacy",
    ) -> SiteLayout:
        """Generate optimal site layout using Gemini AI."""
        logger.info("Generating layout for %d structures on %.0f sqft parcel",
                     len(desired_structures), parcel_features.usable_area_sqft)

        dims = parcel_features.estimated_dimensions
        lot_width = dims.get("width_ft", 100)
        lot_depth = dims.get("depth_ft", 100)
        setbacks = parcel_features.setback_estimate

        structures_desc = []
        for s in desired_structures:
            if s == StructureType.HOME:
                structures_desc.append(f"Home: {home_sqft} sqft total living area")
            elif s == StructureType.DETACHED_GARAGE:
                garage_w = 12 * garage_cars
                structures_desc.append(f"Detached garage: {garage_w}x24 ({garage_cars}-car)")
            elif s == StructureType.SHED:
                structures_desc.append(f"Shed: {shed_sqft} sqft")
            elif s == StructureType.GARDEN:
                structures_desc.append(f"Garden: {garden_sqft} sqft")
            elif s == StructureType.FENCE:
                structures_desc.append(f"Fence: {fence_type} type")
            else:
                structures_desc.append(f"{s.value}")

        layout_prompt = f"""You are a site planning expert. Generate an optimal layout for these structures on a parcel.

PARCEL INFO:
- Dimensions: {lot_width}ft wide × {lot_depth}ft deep
- Usable area: {parcel_features.usable_area_sqft} sqft
- Orientation: {parcel_features.orientation_deg}° from north
- Setbacks: front={setbacks.get('front_ft', 25)}ft, side={setbacks.get('side_ft', 10)}ft, rear={setbacks.get('rear_ft', 20)}ft
- Climate zone: {context_data.climate_zone}
- Prevailing wind: {context_data.prevailing_wind}
- Existing structures: {len(parcel_features.existing_structures)}

DESIRED STRUCTURES:
{chr(10).join(f"- {s}" for s in structures_desc)}

LAYOUT RULES (prioritized):
1. Solar Orientation: Long axis of home E-W for max southern exposure
2. Drainage: Place structures on high ground
3. Access Efficiency: Minimize driveway length
4. Wind Protection: Garage/shed as windbreak on prevailing wind side
5. Privacy: Bedrooms away from street
6. Fire Safety: Defensible space from trees
7. Garden: South-facing, protected from frost
8. Future Expansion: Leave room for additions

Return JSON:
{{
  "structures": [
    {{
      "type": "home|detached_garage|shed|garden|fence|driveway|patio",
      "footprint_sqft": 0,
      "total_sqft": 0,
      "stories": 1,
      "position": {{"x": 0, "y": 0}},
      "rotation_deg": 0,
      "dimensions": {{"width_ft": 0, "depth_ft": 0}},
      "reason": "explanation"
    }}
  ],
  "setbacks": {{"front_ft": 25, "side_ft": 10, "rear_ft": 20}},
  "lot_coverage_pct": 0,
  "usable_yard_sqft": 0,
  "driveway_length_ft": 0,
  "fence_linear_ft": 0,
  "optimization_notes": ["note1", "note2"]
}}

Position uses feet from the northwest corner of the lot. Rotation is clockwise from north."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=layout_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            layout_data = json.loads(response.text)

            structures = []
            for s in layout_data.get("structures", []):
                try:
                    s["type"] = StructureType(s["type"])
                    structures.append(PlacedStructure(**s))
                except (ValueError, KeyError) as err:
                    logger.warning("Skipping invalid structure: %s", err)

            return SiteLayout(
                structures=structures,
                setbacks=layout_data.get("setbacks", setbacks),
                lot_coverage_pct=layout_data.get("lot_coverage_pct", 0),
                usable_yard_sqft=layout_data.get("usable_yard_sqft", 0),
                driveway_length_ft=layout_data.get("driveway_length_ft", 0),
                fence_linear_ft=layout_data.get("fence_linear_ft", 0),
                optimization_notes=layout_data.get("optimization_notes", []),
            )
        except Exception as e:
            logger.error("Layout generation failed: %s", e)
            raise

    async def generate_visualization(
        self,
        address: str,
        style: str = "modern_farmhouse",
        view: str = "birds_eye",
        layout: SiteLayout | None = None,
        layout_description: str | None = None,
    ) -> bytes | None:
        """Generate a photorealistic visualization using Gemini Image Generation.

        Accepts either a full ``SiteLayout`` object or a free-text
        ``layout_description``.  When both are provided the structured
        layout takes precedence.
        """
        if layout and layout.structures:
            structures_desc = "\n".join(
                f"- {s.type.value}: {s.footprint_sqft}sqft at "
                f"({s.position.get('x', 0)}, {s.position.get('y', 0)}), "
                f"{s.dimensions.get('width_ft', 0)}×"
                f"{s.dimensions.get('depth_ft', 0)}ft"
                for s in layout.structures
            )
        elif layout_description:
            structures_desc = layout_description
        else:
            structures_desc = "A residential property with typical Florida structures"

        viz_prompt = f"""Generate a photorealistic {view} view of this site layout:

Location: {address}
Style: {style}
Structures:
{structures_desc}

Requirements:
- Florida landscaping (palm trees, St. Augustine grass, native plants)
- Sunny day with blue sky
- {'Bird\'s-eye view at 45° angle from south' if view == 'birds_eye' else 'Street-level view from the front'}
- Show driveways, walkways, and fencing
- Professional architectural rendering quality"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-image-generation",
                contents=viz_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    temperature=0.8,
                ),
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return part.inline_data.data

            logger.warning("No image in Gemini response")
            return None
        except Exception as e:
            logger.error("Visualization generation failed: %s", e)
            return None
