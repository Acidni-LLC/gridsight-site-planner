"""Configuration module for GridSight SitePlanner."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "gridsight-site-planner"
    app_version: str = "v20260209-001"
    environment: str = "dev"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 7146

    # Google API Keys
    google_gemini_api_key: str = ""
    google_solar_api_key: str = ""
    google_maps_api_key: str = ""

    # Azure Cosmos DB
    cosmos_endpoint: str = "https://acidni-cosmos-dev.documents.azure.com:443/"
    cosmos_database: str = "gridsight-dev"

    # Azure Key Vault (optional — loads secrets on startup)
    azure_key_vault_url: str = ""

    # Application Insights
    applicationinsights_connection_string: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
