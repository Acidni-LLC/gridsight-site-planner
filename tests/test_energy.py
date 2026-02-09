"""Tests for energy estimation service."""

from __future__ import annotations

from src.models import EfficiencyLevel, SolarPotential
from src.services.energy_service import EnergyService


def test_estimate_basic_energy() -> None:
    """Basic energy estimation returns valid results."""
    svc = EnergyService()
    result = svc.estimate(
        cooled_sqft=1800.0,
        lat=28.5,
        lng=-81.4,
        efficiency=EfficiencyLevel.STANDARD,
        solar_potential=None,
        include_solar=False,
    )

    assert result.annual_kwh > 0
    assert result.monthly_avg_kwh > 0
    assert len(result.monthly_breakdown) == 12
    assert result.assumptions is not None


def test_estimate_with_solar_offset() -> None:
    """Energy estimate with solar reduces total consumption."""
    svc = EnergyService()

    # Without solar
    no_solar = svc.estimate(
        cooled_sqft=2000.0,
        lat=28.5,
        lng=-81.4,
        efficiency=EfficiencyLevel.STANDARD,
        solar_potential=None,
        include_solar=False,
    )

    # With solar
    solar = SolarPotential(
        max_panel_count=20,
        panel_capacity_watts=400,
        yearly_kwh_per_kw=1600.0,
        max_array_area_sqft=350.0,
    )
    with_solar = svc.estimate(
        cooled_sqft=2000.0,
        lat=28.5,
        lng=-81.4,
        efficiency=EfficiencyLevel.STANDARD,
        solar_potential=solar,
        include_solar=True,
    )

    assert with_solar.solar_offset_pct > 0
    assert with_solar.annual_kwh < no_solar.annual_kwh


def test_efficiency_levels_affect_consumption() -> None:
    """Higher efficiency results in lower energy usage."""
    svc = EnergyService()

    standard = svc.estimate(1800, 28.5, -81.4, EfficiencyLevel.STANDARD)
    high = svc.estimate(1800, 28.5, -81.4, EfficiencyLevel.HIGH)

    assert high.annual_kwh < standard.annual_kwh


def test_climate_zone_detection() -> None:
    """Climate zone correctly identified by latitude."""
    svc = EnergyService()

    # South Florida (Zone 1A)
    assert svc.get_climate_zone(25.7) == "1A"
    # Central Florida (Zone 2A)
    assert svc.get_climate_zone(28.5) == "2A"
    # North Florida (Zone 3A)
    assert svc.get_climate_zone(30.5) == "3A"


def test_monthly_breakdown_sums_to_annual() -> None:
    """Monthly breakdown values should approximately sum to annual."""
    svc = EnergyService()
    result = svc.estimate(1800, 28.5, -81.4, EfficiencyLevel.STANDARD)

    monthly_sum = sum(m.kwh for m in result.monthly_breakdown)
    # Allow 5% tolerance for rounding
    assert abs(monthly_sum - result.annual_kwh) / result.annual_kwh < 0.05
