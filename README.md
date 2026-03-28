# Motivated Seller Finder

Find and score real estate properties whose owners are most likely to sell — both on-market and off-market. Built for real estate investors who want to identify below-market buying opportunities faster.

---

## What It Does

Aggregates public records and listing data to score each property on a **0–100 Motivation Scale** based on signals like:

- 🔴 Pre-foreclosure / Notice of Default filings
- 🔴 Tax delinquency (2+ years)
- 🔴 Probate / estate / death filings
- 🟠 Bankruptcy filings, active liens
- 🟠 Divorce filings, eviction filings
- 🟠 Code violations, failed inspections
- 🟡 Expired MLS listings, long days on market, price drops
- 🟡 USPS vacancy flags, absentee owners
- 🟢 Long-term ownership, below-market rent, permits not completed
- ...and more

Properties are displayed on an **interactive map** and sortable **property list**, each with a detailed indicator breakdown and (optionally) owner contact info for direct outreach.

---

## Quick Start

### Requirements
- [Docker](https://www.docker.com/get-started) + Docker Compose
- (Optional) API keys for enhanced data (see below)

### Setup

```bash
git clone https://github.com/yourusername/motivated-seller-finder.git
cd motivated-seller-finder

# Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set:
#   JWT_SECRET_KEY (run: python -c "import secrets; print(secrets.token_hex(32))")
#   ADMIN_EMAIL
#   ADMIN_PASSWORD

# Start everything
docker-compose up

# Open the app
open http://localhost:3000
```

On first run, an admin account is created using `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env`.

### First Steps

1. **Log in** at `http://localhost:3000` with your admin credentials
2. **Search for a location** (city, county, or zip) in the top search bar
3. Go to **⚙ Sources** and enable the data sources you want
4. Click **Run Now** on any enabled source to start pulling data
5. Switch to **🗺 Map** or **📋 List** to see scored properties
6. Click any property for the full indicator breakdown

---

## Data Sources

### Free (no API key needed)
| Source | Data Provided |
|---|---|
| County Assessor | Property ownership, assessed value, sale history, absentee owners |
| Court Records | Bankruptcy, probate, divorce filings (via CourtListener) |
| Building Permits | Open/failed permits, code violations (Socrata city portals) |
| USPS Vacancy | Vacancy rates by zip code (HUD API — free key required) |

### Free with API Key
| Source | Key Required | Data Provided |
|---|---|---|
| Zillow / MLS | `RAPIDAPI_KEY` (free tier) | Active listings, DOM, price drops, expired listings |
| Mapillary | `MAPILLARY_CLIENT_TOKEN` (free) | Street view imagery |
| USPS/HUD | HUD API key (free) | Address-level vacancy flags |

### Paid (optional, significantly more data)
| Source | Key Required | Data Provided |
|---|---|---|
| ATTOM | `ATTOM_API_KEY` | Pre-foreclosure NODs, tax delinquency, AVM |
| BatchData | `BATCHDATA_API_KEY` | Skip tracing (owner phone/email), pre-foreclosure |

---

## Invite System

This app is invite-only — only people you invite can access it.

1. Log in as admin and go to `/admin`
2. Enter an email (optional) and click **Generate Invite Link**
3. Share the link with your invitee — they set a password and get access
4. You can deactivate any user at any time from the admin panel

---

## Security

- All Docker ports bind to `127.0.0.1` (localhost only) — your local network is never exposed
- Passwords hashed with bcrypt; JWT stored in httpOnly cookies
- CORS locked to your frontend URL; security headers on all responses
- Secrets never committed to git (`.env` is gitignored)
- For sharing with others: deploy to [Railway](https://railway.app), [Render](https://render.com), or [Fly.io](https://fly.io) — not your home machine

---

## Adding a New County / City

Many data sources work out of the box for major metros (see `county_assessor.py` and `building_permits.py` for the supported list). To add your county:

1. Find your county assessor's open data portal (search "[county name] open data" or look for Socrata)
2. Add the endpoint to `SOCRATA_ENDPOINTS` in `backend/app/data_sources/county_assessor.py`
3. Restart the backend container

---

## Tech Stack

- **Backend**: FastAPI + Python 3.12 + SQLAlchemy (async) + Celery + Redis
- **Database**: PostgreSQL 16 + PostGIS
- **Frontend**: React 18 + TypeScript + Vite + Leaflet.js + Recharts
- **Containerization**: Docker + docker-compose
- **Geocoding**: OpenStreetMap Nominatim (free)

---

## Development

```bash
# Backend only (outside Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev
```

See [CLAUDE.md](./CLAUDE.md) for architecture details and how to add new data sources.

---

## License

MIT
