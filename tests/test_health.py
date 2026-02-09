"""Tests for health endpoint and application setup."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    """Health endpoint returns 200 with service info."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gridsight-site-planner"
    assert "version" in data
    assert data["version"].startswith("v")


def test_health_contains_timestamp() -> None:
    """Health response includes ISO timestamp."""
    response = client.get("/health")
    data = response.json()
    assert "timestamp" in data
    assert "T" in data["timestamp"]  # ISO format check


def test_openapi_docs_available() -> None:
    """OpenAPI docs are accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "GridSight SitePlanner"


def test_cors_headers_present() -> None:
    """CORS headers are returned for allowed origins."""
    response = client.get(
        "/health",
        headers={"Origin": "https://gridsight.acidni.net"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
