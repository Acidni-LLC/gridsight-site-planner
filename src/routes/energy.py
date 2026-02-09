"""Energy estimation and solar analysis routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.models import (
    EnergyEstimateRequest,
    EnergyEstimateResult,
    SolarPotential,
)
from src.services.energy_service import EnergyService
from src.services.solar_service import SolarService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/energy", tags=["energy"])


@router.post("/estimate", response_model=EnergyEstimateResult)
async def estimate_energy(request: EnergyEstimateRequest) -> EnergyEstimateResult:
    """Estimate monthly and yearly energy usage for structures.

    Calculates energy consumption based on:
    - Total cooled square footage
    - Climate zone (derived from latitude)
    - Efficiency level of construction
    - Solar panel potential (from Google Solar API)
    """
    logger.info(
        "Estimating energy for %.0f sqft at (%.4f, %.4f) - %s efficiency",
        request.cooling_sqft or request.home_sqft,
        request.lat,
        request.lng,
        request.efficiency_level.value,
    )

    try:
        energy_svc = EnergyService()
        solar_svc = SolarService()

        # Get solar potential for the location
        solar = await solar_svc.get_solar_potential(request.lat, request.lng)

        # Calculate energy estimate
        cooled_sqft = request.cooling_sqft or request.home_sqft
        result = energy_svc.estimate(
            cooled_sqft=cooled_sqft,
            lat=request.lat,
            lng=request.lng,
            efficiency=request.efficiency_level,
            solar_potential=solar,
            include_solar=request.include_solar,
        )

        return result

    except Exception as e:
        logger.error("Energy estimation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Energy estimation failed: {e}"
        ) from e


@router.get("/solar/{lat}/{lng}", response_model=SolarPotential)
async def get_solar_potential(lat: float, lng: float) -> SolarPotential:
    """Get solar energy potential for a specific location.

    Uses Google Solar API Building Insights to determine:
    - Available roof area for panels
    - Annual sunshine hours
    - Estimated kWh generation per kW installed
    - Panel configuration recommendations
    """
    logger.info("Solar lookup: (%.4f, %.4f)", lat, lng)

    try:
        solar_svc = SolarService()
        result = await solar_svc.get_solar_potential(lat, lng)
        return result

    except Exception as e:
        logger.error("Solar lookup failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Solar potential lookup failed: {e}"
        ) from e
