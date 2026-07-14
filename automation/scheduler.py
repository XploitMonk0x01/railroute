#!/usr/bin/env python3
"""
automation/scheduler.py
────────────────────────
APScheduler-based daemon that polls active watchlist entries on a configurable
interval and upserts fresh availability data into the RailRoute database.

Usage
─────
    # Default: poll every 30 minutes
    python scheduler.py

    # Poll every 15 minutes, run headless
    python scheduler.py --interval 15 --headless

    # Use a specific DB
    python scheduler.py --db-url postgresql://user:pass@host/railroute

Run this in a separate terminal alongside the FastAPI server.
The FastAPI process will automatically serve the updated `seat_availability`
data on the next search request.

Design notes
────────────
• Uses APScheduler's AsyncIOScheduler so all Playwright calls stay on the
  same asyncio event loop — no thread-safety issues.
• A scrape job is skipped if the previous run is still in progress (using
  max_instances=1 on the job).
• SIGINT / SIGTERM shut the scheduler down cleanly and close the browser.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import date

import psycopg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

sys.path.insert(0, os.path.dirname(__file__))
from scraper import IRCTCClient, RouteQuery
from db import upsert_results

# ──────────────────────────────────────────────────────────────
# Logging / console
# ──────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level    = logging.INFO,
    format   = "%(message)s",
    datefmt  = "[%X]",
    handlers = [RichHandler(rich_tracebacks=True)],
)
log     = logging.getLogger("scheduler")
console = Console()


# ──────────────────────────────────────────────────────────────
# Config from env
# ──────────────────────────────────────────────────────────────

DB_URL       = os.getenv("RAILROUTE_DATABASE_URL",        "postgresql://master@127.0.0.1:5432/railroute")
IRCTC_USER   = os.getenv("IRCTC_USER",                    "")
IRCTC_PASS   = os.getenv("IRCTC_PASS",                    "")
HEADLESS     = os.getenv("SCRAPER_HEADLESS", "false").lower() == "true"
MAX_TABS     = int(os.getenv("SCRAPER_MAX_TABS",          "6"))
POLL_MINUTES = int(os.getenv("SCRAPER_POLL_INTERVAL_MINUTES", "30"))


# ──────────────────────────────────────────────────────────────
# Shared client (reused across scheduled runs to avoid login
# overhead on every poll)
# ──────────────────────────────────────────────────────────────

_client: IRCTCClient | None = None


async def _get_client(headless: bool) -> IRCTCClient:
    global _client
    if _client is None:
        _client = IRCTCClient(headless=headless, max_tabs=MAX_TABS)
        await _client.__aenter__()
        if IRCTC_USER and IRCTC_PASS:
            await _client.login(IRCTC_USER, IRCTC_PASS)
        else:
            log.warning(
                "No IRCTC credentials set. "
                "Set IRCTC_USER and IRCTC_PASS in .env for authenticated scrapes."
            )
    return _client


async def _close_client() -> None:
    global _client
    if _client is not None:
        await _client.__aexit__(None, None, None)
        _client = None


# ──────────────────────────────────────────────────────────────
# Watchlist loader
# ──────────────────────────────────────────────────────────────

def _load_watchlist_queries() -> list[RouteQuery]:
    queries: list[RouteQuery] = []
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT source_code, destination_code, journey_date, preferred_class
                    FROM   watchlist
                    WHERE  is_active = TRUE
                      AND  journey_date >= CURRENT_DATE
                    ORDER  BY journey_date
                """)
                for row in cur.fetchall():
                    src, dst, jdate, cls = row
                    queries.append(RouteQuery(
                        from_code  = src,
                        to_code    = dst,
                        date       = jdate if isinstance(jdate, date) else date.fromisoformat(str(jdate)),
                        class_code = cls or "3A",
                    ))
    except Exception as exc:
        log.error("Failed to load watchlist: %s", exc)
    return queries


# ──────────────────────────────────────────────────────────────
# Scheduled job
# ──────────────────────────────────────────────────────────────

_scrape_lock = asyncio.Lock()


async def _scrape_job(headless: bool) -> None:
    """One poll cycle: load watchlist → scrape → upsert."""
    if _scrape_lock.locked():
        log.warning("Previous scrape still running — skipping this cycle.")
        return

    async with _scrape_lock:
        queries = _load_watchlist_queries()
        if not queries:
            log.info("No active watchlist entries — nothing to scrape.")
            return

        log.info("=== Scrape cycle start: %d queries ===", len(queries))
        try:
            client  = await _get_client(headless)
            results = await client.multi_tab_search(queries)
        except Exception as exc:
            log.error("Scrape failed: %s — will retry next cycle.", exc)
            # Reset client so it's re-created (re-logged in) next time
            await _close_client()
            return

        if results:
            try:
                with psycopg.connect(DB_URL) as conn:
                    ok, skipped = upsert_results(conn, results)
                log.info("=== Cycle complete: %d upserted, %d skipped ===", ok, skipped)
            except Exception as exc:
                log.error("DB write failed: %s", exc)
        else:
            log.warning("Scrape returned 0 results.")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

async def _main(interval_minutes: int, headless: bool) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scrape_job,
        trigger     = "interval",
        minutes     = interval_minutes,
        kwargs      = {"headless": headless},
        id          = "irctc_poll",
        max_instances = 1,
        next_run_time = __import__("datetime").datetime.now(),   # run immediately on start
    )
    scheduler.start()

    console.print(
        f"[bold green]RailRoute Scheduler running[/bold green] — "
        f"polling every [bold]{interval_minutes}[/bold] minutes. "
        f"[dim]Press Ctrl+C to stop.[/dim]"
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal(*_: object) -> None:
        log.info("Shutdown signal received.")
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT,  _handle_signal)
    loop.add_signal_handler(signal.SIGTERM, _handle_signal)

    await stop_event.wait()

    log.info("Shutting down scheduler …")
    scheduler.shutdown(wait=False)
    await _close_client()
    log.info("Bye.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog        = "scheduler.py",
        description = "RailRoute watchlist polling daemon",
        formatter_class = argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--interval", type=int, default=POLL_MINUTES,
                        metavar="MINUTES", help="Poll interval in minutes")
    parser.add_argument("--headless", action="store_true",
                        default=HEADLESS, help="Run Chrome headless")
    parser.add_argument("--db-url", default=None, metavar="URL",
                        help="Override RAILROUTE_DATABASE_URL")
    args = parser.parse_args()

    if args.db_url:
        global DB_URL
        DB_URL = args.db_url

    asyncio.run(_main(args.interval, args.headless))


if __name__ == "__main__":
    main()
