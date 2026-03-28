# CLAUDE.md — Motivated Seller Finder

This file provides context for AI-assisted development of this project.

---

## What This Project Does

Finds and scores real estate properties whose owners are likely motivated to sell. Aggregates
public records (foreclosure, court filings, tax delinquency, building permits, etc.) and on-market
data (MLS/Zillow) to compute a 0–100 "motivation score" for each property. Users search by
location, filter by score/status, and view detailed indicator breakdowns to prioritize outreach.

---

## Architecture Overview

```
backend/   FastAPI + Python 3.12 + SQLAlchemy (async) + Celery + Redis
frontend/  React 18 + TypeScript + Vite + Leaflet + Recharts
database/  PostgreSQL 16 + PostGIS
```

All services run in Docker. Entry: `docker-compose up`.

---

## Key Files

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI app, CORS, security headers, router registration |
| `backend/app/config.py` | All env vars via Pydantic Settings |
| `backend/app/database.py` | Async SQLAlchemy engine + session |
| `backend/app/models/` | SQLAlchemy models (property, indicator, score, user, invite, data_source) |
| `backend/app/services/scoring_engine.py` | **Weighted scoring logic** — edit here to change weights |
| `backend/app/services/auth.py` | JWT auth, bcrypt hashing, invite token management |
| `backend/app/data_sources/` | All data source connectors (one file per source) |
| `backend/app/data_sources/registry.py` | Register new sources here |
| `backend/app/api/` | FastAPI route handlers |
| `backend/app/tasks/` | Celery tasks for async data fetch + score recalculation |
| `backend/app/bootstrap.py` | Creates admin user on first run |
| `frontend/src/pages/Dashboard.tsx` | Main dashboard (map/list/sources tabs) |
| `frontend/src/components/` | All UI components |
| `frontend/src/api/index.ts` | All API call functions |
| `frontend/src/types/index.ts` | TypeScript types matching backend schemas |

---

## How to Add a New Data Source

1. Create `backend/app/data_sources/my_source.py`
2. Subclass `DataSource` from `base.py`:

```python
class MySource(DataSource):
    name = "my_source"
    display_name = "My Data Source"
    description = "What it provides"
    is_paid = False
    default_enabled = True

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        # fetch data, return DataSourceResult with .properties and .indicators
        ...

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []  # if you build indicators inline in fetch()
```

3. Add to `backend/app/data_sources/registry.py`:

```python
from app.data_sources.my_source import MySource
ALL_SOURCES = [..., MySource]
```

4. Run a DB migration if you added new models (unlikely for a data source).

---

## How the Scoring Engine Works

File: `backend/app/services/scoring_engine.py`

Each `IndicatorType` has a weight (1–10). Score = `Σ(weight × confidence) / max_possible × 100`.

To adjust weights, edit `INDICATOR_WEIGHTS`. To add a new indicator type:
1. Add to `IndicatorType` enum in `models/indicator.py`
2. Add to `INDICATOR_CATEGORIES` mapping in `models/indicator.py`
3. Add weight to `INDICATOR_WEIGHTS` in `scoring_engine.py`
4. Add a human-readable label in `frontend/src/components/PropertyDetail/PropertyDetail.tsx` → `INDICATOR_LABELS`

---

## Authentication Model

- **Invite-only**: Admin generates invite links from `/admin`. No public registration.
- JWT stored in httpOnly cookies (not localStorage).
- Admin account bootstrapped from `ADMIN_EMAIL` + `ADMIN_PASSWORD` env vars on first run.
- All API routes except `/auth/*` require authentication.

---

## Environment Variables

See `.env.example` for full reference. Required for local dev:

```
DATABASE_URL=postgresql+asyncpg://msf:changeme@db:5432/motivated_seller
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<strong password>
```

Optional (paid sources):
- `ATTOM_API_KEY` — enables ATTOM pre-foreclosure and tax delinquency
- `BATCHDATA_API_KEY` — enables skip tracing (owner phone/email)
- `RAPIDAPI_KEY` — enables Zillow/MLS on-market data
- `GOOGLE_STREET_VIEW_API_KEY` or `MAPILLARY_CLIENT_TOKEN` — street view imagery

---

## Running Tests

```bash
cd backend
pytest tests/
```

Tests use pytest-asyncio. Scoring engine tests are in `tests/test_scoring.py`.

---

## Deployment (Production)

Deploy to Railway, Render, Fly.io, or a DigitalOcean Droplet. Never deploy from your local machine.

1. Set all env vars in the platform dashboard
2. Set `FRONTEND_URL=https://yourdomain.com` and `ENVIRONMENT=production`
3. HTTPS is handled by the platform or your Nginx reverse proxy

Your local computer is never exposed — all traffic goes `User → Cloud → App`.

---

## Data Source Status

| Source | Type | Status |
|---|---|---|
| County Assessor | Free | Integrated (Socrata endpoints for major counties) |
| Court Records | Free | Integrated (CourtListener API) |
| USPS Vacancy | Free | Integrated (HUD API — needs free HUD API key) |
| Building Permits | Free | Integrated (Socrata, major cities) |
| Zillow / MLS | Free tier | Integrated (RapidAPI key needed) |
| ATTOM | Paid | Stubbed, wired in |
| BatchData | Paid | Stubbed, wired in |
| Street View | Free/Paid | Mapillary (free) or Google (paid) |
