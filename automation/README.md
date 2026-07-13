# RailRoute Automation

Pure Playwright (Python) scraper that fetches live IRCTC seat availability and writes it into the RailRoute PostgreSQL database — replacing mock seed data with real-world availability.

---

## Architecture

```
automation/
├── scraper/
│   ├── irctc_client.py   # Core Playwright scraper (stealth, multi-tab, retry)
│   ├── models.py         # RouteQuery + AvailabilityResult dataclasses
│   └── __init__.py
├── db/
│   ├── upsert.py         # Writes results → seat_availability + train_segments
│   └── __init__.py
├── tests/
│   ├── test_models.py    # Unit tests (no DB / browser required)
│   └── test_upsert.py    # Integration tests (requires live DB)
├── scrape.py             # CLI entrypoint
├── scheduler.py          # APScheduler watchlist polling daemon
├── pyproject.toml
└── .env.example
```

### Data Flow

```
scrape.py (CLI) / scheduler.py (daemon)
       │
       ▼
IRCTCClient — Playwright stealth, N parallel tabs
       │
       ▼  list[AvailabilityResult]
db/upsert.py
       ├──▶ seat_availability (upsert — date-specific, real data)
       └──▶ train_segments.available_seats (sync — graph engine reads this)
                   │
                   ▼
       FastAPI /api/v1/search → real availability in route results
```

---

## Setup

### 1. Create a virtual environment

```bash
cd automation
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Install Playwright browsers

```bash
playwright install chromium
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in IRCTC_USER, IRCTC_PASS, and RAILROUTE_DATABASE_URL
```

---

## Usage

### One-shot CLI scrape

```bash
# Single route
python scrape.py --from HWH --to PNBE --date 2026-07-20 --class 3A

# Multiple routes in one run
python scrape.py \
    --route "HWH,PNBE,2026-07-20,3A" \
    --route "HWH,ASN,2026-07-20,SL"

# Scrape all active watchlist entries from the DB
python scrape.py --watchlist

# Dry run (scrape but don't write to DB)
python scrape.py --from HWH --to PNBE --date 2026-07-20 --dry-run

# Headless mode (for servers / CI)
python scrape.py --from HWH --to PNBE --date 2026-07-20 --headless
```

### Background scheduler daemon

```bash
# Poll watchlist every 30 minutes (default)
python scheduler.py

# Poll every 15 minutes, headless
python scheduler.py --interval 15 --headless
```

Run the scheduler alongside your FastAPI server. It automatically stops with `Ctrl+C`.

---

## Running Tests

```bash
# Unit tests only (no DB or browser needed)
pytest tests/test_models.py -v

# All tests (integration tests auto-skip if no DB available)
pytest -v
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `IRCTC_USER` | IRCTC username | _(required for login)_ |
| `IRCTC_PASS` | IRCTC password | _(required for login)_ |
| `RAILROUTE_DATABASE_URL` | PostgreSQL connection string | `postgresql://master@127.0.0.1:5432/railroute` |
| `SCRAPER_HEADLESS` | Run Chrome headless (`true`/`false`) | `false` |
| `SCRAPER_DEFAULT_QUOTA` | Default booking quota | `GN` |
| `SCRAPER_POLL_INTERVAL_MINUTES` | Scheduler poll interval | `30` |
| `SCRAPER_MAX_TABS` | Max parallel browser tabs | `6` |

---

## Notes

### CAPTCHA Handling
IRCTC uses an image CAPTCHA at login. When `SCRAPER_HEADLESS=false` (the default), the browser window opens and pauses for you to solve the CAPTCHA manually. After you click Sign In, the scraper resumes automatically.

In headless/CI mode, login will likely fail due to CAPTCHA. For CI pipelines, pre-export a session cookie file or use an API-based availability source.

### Anti-Bot Stealth
The scraper uses `playwright-stealth` to spoof `navigator.webdriver`, canvas fingerprints, and user-agent strings. This passes most bot-detection checks but is not guaranteed to work if IRCTC updates their Cloudflare configuration.

### Legal Notice
Automated scraping may violate IRCTC's Terms of Service. Use for personal / research purposes only. Consider the official Indian Railways Data API at `data.gov.in` as an alternative data source.
