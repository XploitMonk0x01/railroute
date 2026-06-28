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
  - Transfer-aware alternative route search.
  - Direct unavailable train detection.
  - Route ranking presets for default, fastest, cheapest, least transfers, and best availability.
  - Cycle prevention for candidate routes.
- Data layer:
  - PostgreSQL schema in `backend/schema.sql`.
  - Repository abstraction with in-memory and PostgreSQL implementations.
  - Seed script in `backend/seed_db.py`.
- Frontend:
  - Next.js app shell with search UI components, route cards, filter controls, station selector, and API client.

## HWH to PNBE Scenario

The MVP dataset now supports the requested scenario:

- Source: `HWH` Howrah Junction
- Destination: `PNBE` Patna Junction
- Journey date: `2026-06-28`
- Direct train: `12351` Howrah Patna Express
- Direct availability: `WL`, so `direct_available` is `false`
- Alternative routes:
  - `HWH -> BWN -> PNBE`
  - `HWH -> ASN -> PNBE`

Expected API request:

```json
{
  "source": "HWH",
  "destination": "PNBE",
  "date": "2026-06-28",
  "class": "3A",
  "constraints": {
    "max_transfers": 2,
    "max_wait_min": 240
  }
}
```

## Verification

Covered by tests:

- HWH to PNBE returns `direct_available: false`.
- Direct HWH to PNBE train is included as waitlisted metadata.
- Alternatives are returned and terminate at PNBE.
- Existing route search, station search, health route, scoring, wait, budget, transfer, and cycle behavior remain covered.

## Next Work

- Make seat availability date-specific instead of segment-level.
- Add Redis route and availability caching.
- Add background graph rebuild and availability sync jobs.
- Wire the frontend search page fully against live backend responses.
- Add user-backed watchlist persistence and notification processing.
