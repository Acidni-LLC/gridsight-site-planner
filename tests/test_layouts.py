"""Tests for structure templates and layout route basics."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_get_templates_returns_list() -> None:
    """Templates endpoint returns a non-empty list."""
    response = client.get("/api/v1/layouts/templates")
    assert response.status_code == 200

    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) >= 8  # We defined 10 templates


def test_templates_contain_home() -> None:
    """Templates include a Home structure type."""
    response = client.get("/api/v1/layouts/templates")
    templates = response.json()

    home = next((t for t in templates if t["type"] == "home"), None)
    assert home is not None
    assert home["default_sqft"] > 0
    assert home["requires_setback"] is True


def test_templates_contain_required_fields() -> None:
    """Every template has all required fields."""
    response = client.get("/api/v1/layouts/templates")
    templates = response.json()

    required_fields = {
        "type", "name", "default_sqft", "min_sqft",
        "max_sqft", "description", "requires_setback",
    }

    for template in templates:
        missing = required_fields - set(template.keys())
        assert not missing, f"Template {template.get('name')} missing: {missing}"
