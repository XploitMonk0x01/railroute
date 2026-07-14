# RailRoute Project Progress

## Current Status

RailRoute is an MVP train-only route planning system based on the architecture in `railroute-architecture.md`. The project now has a FastAPI backend, a PostgreSQL schema/seed path, a NetworkX-backed route graph, and a Next.js frontend shell.

## Implemented

- Backend API:
  - `POST /api/v1/search`
  - `GET /api/v1/stations`
  - `GET /api/v1/stations/top-junctions`
  - `GET /api/v1/health`
  - Initial auth and watchlist route modules are present.
- Route engine:
  - Graph-based train segment discovery.
  - Transfer-aware alternative route search allowing up to 24 hour connections.
  - Direct unavailable train detection.
  - Route ranking presets for default, fastest, cheapest, least transfers, and best availability.
  - Cycle prevention for candidate routes.
- Live Data Scraping:
  - Integrated ConfirmTkt automation scraper using Playwright.
  - Automatically fetches availability for direct and connecting routes simultaneously.
  - Syncs live scraped seat availability into the graph engine for immediate routing.
- Data layer:
  - PostgreSQL schema in `backend/schema.sql`.
  - Repository abstraction with in-memory and PostgreSQL implementations.
  - Seed script in `backend/seed_db.py` connecting West (ADI/BRC/NDLS) and East (HWH/PNBE) corridors.
- Frontend:
  - Next.js app shell with search UI components, route cards, filter controls, station selector, and API client.

## Scenarios Handled

The MVP dataset now successfully connects disjoint regions and fetches live data:

- Source: `BRC` (Vadodara)
- Destination: `PNBE` (Patna)
- Direct availability check: Verified via ConfirmTkt.
- Alternative routes:
  - `BRC -> KOTA -> NDLS -> PNBE` (Overnight layovers supported up to 24h)
  - `BRC -> KOTA -> NDLS -> HWH -> PNBE`

## Verification

Covered by tests and live system validation:

- End-to-end routing successfully connects BRC and PNBE.
- Live scraper launches Chromium and correctly parses waitlist/availability data.
- Default constraints updated to support longer transfers (`max_wait_min=1440`).
- Mixed-class connections (e.g., CC to 3A) are handled properly in the search.

## Next Work

- Add Redis route and availability caching.
- Add background graph rebuild and availability sync jobs.
- Wire the frontend search page fully against live backend responses.
- Add user-backed watchlist persistence and notification processing.
