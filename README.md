# RailRoute AI

RailRoute AI is a Smart Train Route Planner for Indian Railways. Our intelligent graph engine discovers alternative multi-hop routes (with 1-3 transfers) when your direct train is sold out or waitlisted. It dynamically ranks routes based on travel time, fare, transfers, and seat availability, allowing users to customize their travel priorities.

## Key Features

- **Multi-Hop Route Discovery:** Automatically finds alternative routes when direct tickets are unavailable.
- **Smart Route Scoring:** Ranks alternatives based on customizable weights (time, fare, transfers, wait time).
- **Waitlist Monitoring:** Built-in mechanisms to support future waitlist alert features.
- **Modern Tech Stack:** Blazing fast FastAPI backend paired with a beautiful Next.js frontend.

---

## Tech Stack

- **Backend Language**: Python 3.11+
- **Backend Framework**: FastAPI
- **Graph Engine**: NetworkX (In-memory route computation)
- **Frontend Framework**: Next.js 16 (React 19)
- **State Management**: Zustand
- **Styling**: Tailwind CSS v4 + Shadcn UI
- **Database**: PostgreSQL 16 (psycopg3)

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Node.js 20 or higher
- Python 3.11 or higher
- PostgreSQL 15 or higher (or Docker for running Postgres)
- npm or pnpm

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/railroute.git
cd railroute
```

### 2. Backend Setup

Set up a virtual environment and install the Python dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

### 3. Database Setup

Ensure PostgreSQL is running locally on port `5432` with a user `master`. Create the database, load the schema, and run the seed script:

```bash
# Create the database
createdb railroute

# Load the schema
psql -d railroute -f schema.sql

# Seed the MVP dataset (includes the HWH -> PNBE waitlist scenario)
python seed_db.py
```

### 4. Start the Backend Server

Start the FastAPI application with Uvicorn (hot-reloading enabled):

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
API Documentation will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Frontend Setup

In a new terminal window, navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
```

### 6. Start the Frontend Server

```bash
npm run dev -- -p 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser. You can test the routing engine by searching for a route from `HWH` to `PNBE` on `2026-06-28`.

---

## Architecture

### Directory Structure

```text
railroute/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes and dependencies
│   │   ├── core/         # Graph engine and core configuration
│   │   ├── models/       # Domain and data models
│   │   ├── repositories/ # Database repository layer (PgRailRepository)
│   │   ├── schemas/      # Pydantic models for API serialization
│   │   └── services/     # Route calculation and station search services
│   ├── tests/            # Pytest test suite
│   ├── schema.sql        # PostgreSQL schema definitions
│   └── seed_db.py        # Database seeding script
├── frontend/
│   ├── app/              # Next.js App Router pages and layouts
│   ├── components/       # Reusable UI components (shadcn/ui)
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # API utilities and formatting helpers
│   └── store/            # Zustand global state management
└── railroute-architecture.md # Detailed architecture document
```

### Request Lifecycle

1. **User Action:** The user inputs a source (`HWH`), destination (`PNBE`), date, and preferences into the Next.js frontend.
2. **API Call:** The frontend (`lib/api.ts`) sends a POST request to the FastAPI backend (`/api/v1/search`).
3. **Controller & Service:** The `RouteService` validates the request and begins the graph traversal.
4. **Graph Engine:** NetworkX traverses the in-memory graph (pre-built from PostgreSQL `train_segments` data) using a modified Dijkstra's algorithm to find the optimal paths, adhering to transfer limits and wait times.
5. **Ranking:** The `RouteService` scores and ranks the discovered routes based on the user's selected `filter_preset` (e.g., fastest, cheapest).
6. **Response:** FastAPI serializes the ranked routes into a JSON response using Pydantic models.
7. **Render:** The Zustand store updates on the frontend, triggering the React UI to display the alternative multi-hop routes.

### Database Schema

```text
stations
├── code (string, PK)
├── name (string)
├── city (string)
├── state (string)
├── score (integer)
└── is_junction (boolean)

trains
├── number (string, PK)
├── name (string)
├── train_type (string)
└── run_days (integer array)

train_segments
├── id (bigint, PK)
├── train_number (string, FK -> trains)
├── from_station (string, FK -> stations)
├── to_station (string, FK -> stations)
├── departure (time)
├── arrival (time)
├── duration_min (integer)
├── distance_km (integer)
├── fare (numeric)
├── class_code (string)
├── available_seats (integer)
└── run_days (integer array)
```
*(Note: Refer to `backend/schema.sql` for the full schema including `train_halts`, `seat_availability`, and `users` tables).*

---

## Environment Variables

### Backend Configuration

Configuration is managed via Pydantic Settings. You can override defaults using environment variables prefixed with `RAILROUTE_`.

| Variable | Description | Default |
| --- | --- | --- |
| `RAILROUTE_DATABASE_URL` | PostgreSQL connection string | `postgresql://master@127.0.0.1:5432/railroute` |
| `RAILROUTE_DEFAULT_TOP_K_ROUTES` | Max routes returned in search | `5` |
| `RAILROUTE_DEFAULT_MAX_TRANSFERS` | Max transfers allowed per route | `2` |

---

## Available Scripts

### Backend (`/backend`)
| Command | Description |
| --- | --- |
| `python -m uvicorn app.main:app --reload` | Start the development server |
| `python seed_db.py` | Drop (optionally) and seed the database |
| `pytest` | Run the Pytest test suite |

### Frontend (`/frontend`)
| Command | Description |
| --- | --- |
| `npm run dev` | Start the Next.js development server |
| `npm run build` | Build the application for production |
| `npm run start` | Start the production server |
| `npm run lint` | Run ESLint checks |
| `npm run format` | Run Prettier code formatting |

---

## Testing

The backend includes a comprehensive test suite using Pytest. Tests are divided into unit tests for routing logic (`test_route_service.py`) and integration tests for API endpoints (`test_api_routes.py`).

### Running Tests

```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest

# Run tests with verbose output
pytest -v
```

---

## Troubleshooting

### No Alternative Routes Found

**Error:** The API returns `{"direct_available": false, "alternatives": []}` for a route that should have alternatives.
**Solution:** Ensure your PostgreSQL database has been seeded properly. Run `python seed_db.py` in the `backend` directory to load the `train_segments` table with the mock data, then restart your FastAPI server.

### Database Connection Refused

**Error:** `psycopg_pool.PoolClosed` or `Connection refused`.
**Solution:** Check that PostgreSQL is actively running on port `5432` and that the connection string inside `backend/app/core/config.py` is correct. If you are using a different user or password, specify `RAILROUTE_DATABASE_URL` as an environment variable before starting Uvicorn.
