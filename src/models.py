"""Pydantic models for GridSight SitePlanner API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── Enums ─────────────────────────────────────────────────────────────────────


class StructureType(str, Enum):
    """Types of structures that can be placed on a site."""

    HOME = "home"
    GARAGE = "garage"
    DETACHED_GARAGE = "detached_garage"
    SHED = "shed"
    FENCE = "fence"
    GARDEN = "garden"
    DRIVEWAY = "driveway"
    PATIO = "patio"
    DECK = "deck"
    POOL = "pool"
    GREENHOUSE = "greenhouse"
    WORKSHOP = "workshop"
    BARN = "barn"


class EfficiencyLevel(str, Enum):
    """Building energy efficiency level."""

    EFFICIENT = "efficient"
    STANDARD = "standard"
    POOR = "poor"


class ProjectStatus(str, Enum):
    """Status of a site planning project."""

    CREATED = "created"
    ANALYZING = "analyzing"
    LAYOUT_GENERATED = "layout_generated"
    ENERGY_ESTIMATED = "energy_estimated"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Request Models ────────────────────────────────────────────────────────────


class ParcelAnalyzeRequest(BaseModel):
    """Request to analyze a parcel of land."""

    address: str = Field(..., description="Street address of the parcel")
    lat: float | None = Field(None, description="Latitude (optional if address provided)")
    lng: float | None = Field(None, description="Longitude (optional if address provided)")
    desired_structures: list[StructureType] = Field(
        default_factory=lambda: [StructureType.HOME],
        description="List of structures to place on the site",
    )
    home_sqft: int = Field(2400, ge=500, le=20000, description="Home living area in sqft")
    cooling_sqft: int | None = Field(None, description="Cooled area sqft (defaults to home_sqft)")
    garage_cars: int = Field(2, ge=0, le=4, description="Number of garage car bays")
    shed_sqft: int = Field(120, ge=0, le=1000, description="Shed area in sqft")
    garden_sqft: int = Field(200, ge=0, le=5000, description="Garden area in sqft")
    fence_type: str = Field("privacy", description="Fence type: privacy, decorative, farm, none")
    efficiency_level: EfficiencyLevel = Field(
        EfficiencyLevel.STANDARD, description="Building efficiency level"
    )


class LayoutGenerateRequest(BaseModel):
    """Request to generate or regenerate a site layout."""

    project_id: str = Field("", description="Project ID from parcel analysis")
    user_id: str = Field("default-user", description="User ID for project ownership")
    parcel_sqft: float = Field(10000, ge=500, description="Total parcel area in sqft")
    parcel_width_ft: float = Field(100, ge=10, description="Parcel width in feet")
    parcel_depth_ft: float = Field(100, ge=10, description="Parcel depth in feet")
    structures: list[StructureType] = Field(
        default_factory=lambda: [StructureType.HOME],
        description="Structures to place on the site",
    )
    constraints: dict[str, str] = Field(
        default_factory=dict, description="Additional layout constraints"
    )
    preferences: dict[str, str] = Field(
        default_factory=dict, description="User preferences for layout generation"
    )


class EnergyEstimateRequest(BaseModel):
    """Request to estimate energy usage for a site."""

    lat: float = Field(..., description="Latitude of the site")
    lng: float = Field(..., description="Longitude of the site")
    home_sqft: int = Field(2400, ge=500, le=20000, description="Home living area in sqft")
    cooling_sqft: int | None = Field(None, description="Cooled area sqft (defaults to home_sqft)")
    stories: int = Field(1, ge=1, le=3, description="Number of stories")
    efficiency_level: EfficiencyLevel = Field(EfficiencyLevel.STANDARD)
    include_solar: bool = Field(True, description="Include solar potential analysis")


class VisualizeRequest(BaseModel):
    """Request to generate a visualization of the site layout."""

    project_id: str = Field("", description="Project ID with completed layout")
    layout_id: str = Field("", description="Layout ID for visualization reference")
    layout_description: str = Field("", description="Text description of the layout for rendering")
    address: str = Field("", description="Address for contextual rendering")
    style: str = Field("modern_farmhouse", description="Architectural style for rendering")
    view: str = Field("birds_eye", description="View angle: birds_eye, street_view, plan_2d")


# ─── Parcel Analysis Models ───────────────────────────────────────────────────


class BoundingBox(BaseModel):
    """Bounding box for a detected object (normalized 0-1000)."""

    y_min: int
    x_min: int
    y_max: int
    x_max: int


class DetectedStructure(BaseModel):
    """An existing structure detected on the parcel."""

    type: str
    bbox: BoundingBox
    area_estimate_sqft: float
    confidence: float = 0.0


class ParcelFeatures(BaseModel):
    """Features extracted from parcel satellite analysis."""

    parcel_boundary: list[list[int]] = Field(
        default_factory=list, description="Polygon coordinates (normalized 0-1000)"
    )
    existing_structures: list[DetectedStructure] = Field(default_factory=list)
    vegetation_areas: list[dict] = Field(default_factory=list)
    access_points: list[dict] = Field(default_factory=list)
    orientation_deg: float = Field(0.0, description="Compass bearing of primary frontage")
    usable_area_sqft: float = Field(0.0)
    estimated_dimensions: dict[str, float] = Field(
        default_factory=dict, description="width_ft, depth_ft"
    )
    setback_estimate: dict[str, float] = Field(
        default_factory=lambda: {"front_ft": 25, "side_ft": 10, "rear_ft": 20}
    )


class ContextData(BaseModel):
    """Location context from Maps Grounding."""

    zoning: str = ""
    climate_zone: str = ""
    avg_temp_high_f: float = 0.0
    avg_temp_low_f: float = 0.0
    prevailing_wind: str = ""
    soil_type: str = ""
    flood_zone: str = ""
    nearby_utilities: list[str] = Field(default_factory=list)


class ParcelAnalysisResult(BaseModel):
    """Complete result from parcel analysis."""

    parcel_features: ParcelFeatures
    context_data: ContextData
    satellite_image_url: str = ""
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Layout Models ────────────────────────────────────────────────────────────


class PlacedStructure(BaseModel):
    """A structure placed on the site layout."""

    type: StructureType
    footprint_sqft: float
    total_sqft: float = 0.0
    stories: int = 1
    position: dict[str, float] = Field(description="x, y in feet from lot origin")
    rotation_deg: float = 0.0
    dimensions: dict[str, float] = Field(description="width_ft, depth_ft")
    reason: str = Field("", description="Rationale for placement")


class SiteLayout(BaseModel):
    """Generated site layout with all structures."""

    layout_id: str = ""
    structures: list[PlacedStructure] = Field(default_factory=list)
    setbacks: dict[str, float] = Field(
        default_factory=lambda: {"front_ft": 25, "side_ft": 10, "rear_ft": 20}
    )
    lot_coverage_pct: float = 0.0
    usable_yard_sqft: float = 0.0
    driveway_length_ft: float = 0.0
    fence_linear_ft: float = 0.0
    optimization_notes: list[str] = Field(default_factory=list)


# ─── Energy Models ─────────────────────────────────────────────────────────────


class MonthlyEnergy(BaseModel):
    """Energy estimate for a single month."""

    month: str
    kwh: float
    cost: float
    primary_load: str  # "cooling", "heating", "base"


class SolarPotential(BaseModel):
    """Solar potential analysis."""

    max_panels: int = 0
    annual_production_kwh: float = 0.0
    offset_pct: float = 0.0
    estimated_savings_annual: float = 0.0
    sunshine_hours_per_year: float = 0.0
    roof_area_sqft: float = 0.0


class EnergyAssumptions(BaseModel):
    """Assumptions used in energy calculation."""

    climate_zone: str
    cdd: int  # Cooling Degree Days
    hdd: int  # Heating Degree Days
    rate_per_kwh: float
    efficiency_level: EfficiencyLevel
    home_sqft: int
    cooling_sqft: int


class EnergyEstimateResult(BaseModel):
    """Complete energy estimation result."""

    annual_total_kwh: float = 0.0
    annual_total_cost: float = 0.0
    annual_cooling_kwh: float = 0.0
    annual_heating_kwh: float = 0.0
    annual_base_kwh: float = 0.0
    monthly: list[MonthlyEnergy] = Field(default_factory=list)
    solar_potential: SolarPotential | None = None
    assumptions: EnergyAssumptions | None = None


# ─── Response Models ───────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "gridsight-site-planner"
    version: str = ""
    environment: str = ""
    timestamp: str = ""


class ProjectResponse(BaseModel):
    """Full project response including all analysis stages."""

    id: str
    user_id: str = "default-user"
    name: str = ""
    address: str = ""
    lat: float = 0.0
    lng: float = 0.0
    status: ProjectStatus = ProjectStatus.CREATED
    parcel_analysis: ParcelAnalysisResult | None = None
    layout: SiteLayout | None = None
    energy_estimate: EnergyEstimateResult | None = None
    visualizations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StructureTemplate(BaseModel):
    """Template for a structure type."""

    type: StructureType
    name: str
    default_sqft: float = 0.0
    min_sqft: float = 0.0
    max_sqft: float = 0.0
    description: str = ""
    requires_setback: bool = False
    default_setback_ft: float = 0.0
    variants: list[str] = Field(default_factory=list)
