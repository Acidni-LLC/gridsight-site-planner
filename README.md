# GridSight SitePlanner

**AI-powered site layout — from your parcel to your power bill**

GridSight SitePlanner analyzes parcels of land using Google's latest AI capabilities, generates optimal site layouts for structures (homes, garages, sheds, fences, gardens), and estimates monthly/yearly energy usage.

## Features

- 🛰️ **Parcel Analysis** — Satellite imagery analysis with Gemini 2.5 Flash
- 🏠 **Layout Generation** — AI-optimized structure placement with solar orientation
- ⚡ **Energy Estimation** — Monthly/yearly kWh and cost projections
- ☀️ **Solar Potential** — Google Solar API integration for panel placement
- 🎨 **Visualization** — Photorealistic renderings with Gemini Image Generation
- 🗺️ **Maps Context** — Location-aware data via Gemini Maps Grounding

## Quick Start

```bash
# Clone
git clone https://github.com/Acidni-LLC/gridsight-site-planner.git
cd gridsight-site-planner

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run locally
uvicorn src.main:app --host 0.0.0.0 --port 7146 --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/parcels/analyze` | Analyze a parcel |
| `POST` | `/api/v1/layouts/generate` | Generate site layout |
| `POST` | `/api/v1/energy/estimate` | Estimate energy usage |
| `GET` | `/api/v1/energy/solar/{lat}/{lng}` | Get solar potential |
| `POST` | `/api/v1/visualize` | Generate visualization |
| `GET` | `/api/v1/templates/structures` | List structure templates |

## Tech Stack

- **Python 3.12+** with FastAPI
- **Google Gemini 2.5 Flash** — Image Understanding + Maps Grounding
- **Google Solar API** — Building Insights
- **Azure Container Apps** — Hosting
- **Cosmos DB Serverless** — Data storage

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_GEMINI_API_KEY` | Gemini API key | ✅ |
| `GOOGLE_SOLAR_API_KEY` | Solar API key | ✅ |
| `GOOGLE_MAPS_API_KEY` | Maps Static API key | ✅ |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint | ✅ |
| `COSMOS_DATABASE` | Database name | ✅ |
| `AZURE_KEY_VAULT_URL` | Key Vault URL | Optional |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights | Optional |

## Architecture

See [Design Document](docs/site-planner-design.md) for complete architecture details.

## License

Proprietary — Acidni LLC © 2026
