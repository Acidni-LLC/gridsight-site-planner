"""Energy estimation service for residential buildings."""

from __future__ import annotations

import logging

from src.models import (
    EfficiencyLevel,
    EnergyAssumptions,
    EnergyEstimateResult,
    MonthlyEnergy,
    SolarPotential,
)

logger = logging.getLogger(__name__)

# ─── Climate Zone Data ─────────────────────────────────────────────────────────

# Monthly CDD/HDD distribution factors (fraction of annual total per month)
# Based on typical Florida climate patterns
MONTHLY_CDD_FACTORS = {
    "January": 0.02, "February": 0.03, "March": 0.05, "April": 0.08,
    "May": 0.12, "June": 0.16, "July": 0.18, "August": 0.17,
    "September": 0.12, "October": 0.05, "November": 0.02, "December": 0.01,
}

MONTHLY_HDD_FACTORS = {
    "January": 0.25, "February": 0.20, "March": 0.12, "April": 0.05,
    "May": 0.01, "June": 0.00, "July": 0.00, "August": 0.00,
    "September": 0.00, "October": 0.02, "November": 0.10, "December": 0.25,
}

MONTH_NAMES = list(MONTHLY_CDD_FACTORS.keys())

# Climate zone lookup by approximate ZIP code ranges (Florida-focused)
CLIMATE_ZONES: dict[str, dict] = {
    "1A": {"cdd": 4000, "hdd": 200, "rate": 0.14, "description": "Hot-Humid (South FL)"},
    "2A": {"cdd": 2800, "hdd": 1200, "rate": 0.13, "description": "Hot-Humid (Central/North FL)"},
    "3A": {"cdd": 2000, "hdd": 2000, "rate": 0.12, "description": "Warm-Humid (Panhandle)"},
}

# Efficiency factors for cooling and heating
EFFICIENCY_FACTORS = {
    EfficiencyLevel.EFFICIENT: {"cooling": 0.35, "heating": 0.15, "base": 3.0},
    EfficiencyLevel.STANDARD: {"cooling": 0.50, "heating": 0.25, "base": 3.5},
    EfficiencyLevel.POOR: {"cooling": 0.70, "heating": 0.40, "base": 4.5},
}


def get_climate_zone(lat: float) -> str:
    """Determine IECC climate zone from latitude (Florida-focused)."""
    if lat < 26.5:
        return "1A"  # South Florida (Miami, Fort Lauderdale)
    elif lat < 30.5:
        return "2A"  # Central/North Florida (Orlando, Jacksonville, Hastings)
    else:
        return "3A"  # Florida Panhandle (Pensacola, Tallahassee)


class EnergyService:
    """Service for estimating residential energy usage."""

    def estimate(
        self,
        home_sqft: int,
        cooling_sqft: int | None,
        lat: float,
        efficiency: EfficiencyLevel = EfficiencyLevel.STANDARD,
        solar_potential: SolarPotential | None = None,
    ) -> EnergyEstimateResult:
        """Calculate estimated energy usage for a residential building.

        Energy Model:
            Base Load = sqft × base_factor kWh/sqft/year
            Cooling Load = cooling_sqft × CDD × cooling_efficiency / 1000
            Heating Load = sqft × HDD × heating_efficiency / 1000
            Total Annual = Base + Cooling + Heating - Solar_Offset
        """
        if cooling_sqft is None:
            cooling_sqft = home_sqft

        # Determine climate zone
        zone_id = get_climate_zone(lat)
        zone = CLIMATE_ZONES[zone_id]
        cdd = zone["cdd"]
        hdd = zone["hdd"]
        rate = zone["rate"]

        # Get efficiency factors
        factors = EFFICIENCY_FACTORS[efficiency]

        # Annual calculations
        base_kwh = home_sqft * factors["base"]
        cooling_kwh = cooling_sqft * cdd * factors["cooling"] / 1000
        heating_kwh = home_sqft * hdd * factors["heating"] / 1000
        total_annual = base_kwh + cooling_kwh + heating_kwh

        logger.info(
            "Energy estimate: %d sqft in zone %s — Base=%.0f, Cool=%.0f, Heat=%.0f, "
            "Total=%.0f kWh/yr",
            home_sqft, zone_id, base_kwh, cooling_kwh, heating_kwh, total_annual,
        )

        # Monthly breakdown
        monthly: list[MonthlyEnergy] = []
        for month in MONTH_NAMES:
            month_base = base_kwh / 12
            month_cooling = cooling_kwh * MONTHLY_CDD_FACTORS[month]
            month_heating = heating_kwh * MONTHLY_HDD_FACTORS[month]
            month_total = month_base + month_cooling + month_heating

            # Determine primary load for the month
            if month_cooling > month_heating and month_cooling > month_base:
                primary = "cooling"
            elif month_heating > month_cooling and month_heating > month_base:
                primary = "heating"
            else:
                primary = "base"

            monthly.append(MonthlyEnergy(
                month=month,
                kwh=round(month_total, 1),
                cost=round(month_total * rate, 2),
                primary_load=primary,
            ))

        # Solar offset
        if solar_potential and solar_potential.annual_production_kwh > 0:
            solar_potential.offset_pct = round(
                (solar_potential.annual_production_kwh / total_annual) * 100, 1
            )

        assumptions = EnergyAssumptions(
            climate_zone=zone_id,
            cdd=cdd,
            hdd=hdd,
            rate_per_kwh=rate,
            efficiency_level=efficiency,
            home_sqft=home_sqft,
            cooling_sqft=cooling_sqft,
        )

        return EnergyEstimateResult(
            annual_total_kwh=round(total_annual, 1),
            annual_total_cost=round(total_annual * rate, 2),
            annual_cooling_kwh=round(cooling_kwh, 1),
            annual_heating_kwh=round(heating_kwh, 1),
            annual_base_kwh=round(base_kwh, 1),
            monthly=monthly,
            solar_potential=solar_potential,
            assumptions=assumptions,
        )
