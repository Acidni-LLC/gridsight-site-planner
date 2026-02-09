"""Google Solar API service for building insights and energy estimation."""

from __future__ import annotations

import logging

import httpx

from src.config import get_settings
from src.models import SolarPotential

logger = logging.getLogger(__name__)


class SolarService:
    """Service for Google Solar API interactions."""

    BASE_URL = "https://solar.googleapis.com/v1"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.google_solar_api_key

    async def get_building_insights(
        self, lat: float, lng: float, quality: str = "HIGH"
    ) -> dict:
        """Get building insights from Google Solar API."""
        url = f"{self.BASE_URL}/buildingInsights:findClosest"
        params = {
            "location.latitude": lat,
            "location.longitude": lng,
            "requiredQuality": quality,
            "key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "Solar API: Got building insights for (%.4f, %.4f) - "
                    "max sunshine: %.0f hrs/yr",
                    lat, lng,
                    data.get("solarPotential", {}).get("maxSunshineHoursPerYear", 0),
                )
                return data
            except httpx.HTTPStatusError as e:
                logger.warning("Solar API error %d: %s", e.response.status_code, e.response.text)
                return {}
            except Exception as e:
                logger.error("Solar API request failed: %s", e)
                return {}

    async def get_solar_potential(self, lat: float, lng: float) -> SolarPotential:
        """Get solar potential analysis for a location."""
        data = await self.get_building_insights(lat, lng)

        if not data or "solarPotential" not in data:
            logger.warning("No solar data available for (%.4f, %.4f), using estimates", lat, lng)
            return self._estimate_solar_potential(lat)

        solar = data["solarPotential"]
        panel_configs = solar.get("solarPanelConfigs", [])

        if panel_configs:
            # Use the maximum panel configuration
            max_config = panel_configs[-1]
            max_panels = max_config.get("panelsCount", 0)
            annual_kwh = max_config.get("yearlyEnergyDcKwh", 0)
        else:
            max_panels = 0
            annual_kwh = 0

        # Calculate roof area from segments
        roof_segments = solar.get("roofSegmentStats", [])
        total_roof_sqft = sum(
            seg.get("stats", {}).get("areaMeters2", 0) * 10.764  # m² to sqft
            for seg in roof_segments
        )

        sunshine_hours = solar.get("maxSunshineHoursPerYear", 0)

        # Estimate savings
        rate_per_kwh = 0.13  # Florida average
        estimated_savings = annual_kwh * rate_per_kwh * 0.85  # 85% DC-to-AC efficiency

        return SolarPotential(
            max_panels=max_panels,
            annual_production_kwh=annual_kwh * 0.85,  # DC to AC
            offset_pct=0,  # Calculated later against total usage
            estimated_savings_annual=estimated_savings,
            sunshine_hours_per_year=sunshine_hours,
            roof_area_sqft=total_roof_sqft,
        )

    def _estimate_solar_potential(self, lat: float) -> SolarPotential:
        """Estimate solar potential when API data isn't available."""
        # Use latitude-based estimation for Florida
        # Peak sun hours roughly: 5.5 (N FL) to 6.0 (S FL)
        peak_sun_hours = 5.5 + (30 - lat) * 0.1  # Rough approximation
        peak_sun_hours = max(4.5, min(6.5, peak_sun_hours))

        # Assume standard 2400 sqft home = ~600 sqft usable roof for solar
        usable_roof_sqft = 600
        panel_sqft = 17.5  # Average residential panel
        max_panels = int(usable_roof_sqft / panel_sqft)
        watts_per_panel = 400
        system_kw = max_panels * watts_per_panel / 1000

        annual_kwh = system_kw * peak_sun_hours * 365 * 0.80  # 80% system efficiency

        return SolarPotential(
            max_panels=max_panels,
            annual_production_kwh=annual_kwh,
            offset_pct=0,
            estimated_savings_annual=annual_kwh * 0.13,
            sunshine_hours_per_year=peak_sun_hours * 365,
            roof_area_sqft=usable_roof_sqft,
        )
