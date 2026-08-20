import sys
import os
import asyncio
import concurrent.futures
from datetime import date
from typing import List
from pathlib import Path

# Load .env file so os.getenv() can read IRCTC_USER, IRCTC_PASS, etc.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[3] / "backend" / ".env"
    if not _env_path.exists():
        _env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(_env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on shell env vars

# Ensure automation module is in path
automation_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../automation"))
if automation_path not in sys.path:
    sys.path.insert(0, automation_path)

from scraper.irctc_client import IRCTCClient
from scraper.models import RouteQuery, AvailabilityResult
from db.upsert import upsert_results
from app.database import db_pool


def _run_scraper_sync(
    queries: List[RouteQuery],
    headless: bool,
    max_tabs: int,
) -> List[AvailabilityResult]:
    """
    Run the Playwright scraper in a fresh ProactorEventLoop.

    On Windows, Uvicorn's event loop (SelectorEventLoop) does NOT support
    asyncio.create_subprocess_exec, which Playwright needs to launch the
    browser driver.  We solve this by spinning up a new ProactorEventLoop
    inside a worker thread.
    """
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_scrape_async(queries, headless, max_tabs))
    finally:
        loop.close()


async def _scrape_async(
    queries: List[RouteQuery],
    headless: bool,
    max_tabs: int,
) -> List[AvailabilityResult]:
    """Actual async scraping logic — runs inside the worker thread's loop."""
    async with IRCTCClient(headless=headless, max_tabs=max_tabs) as client:
        return await client.multi_tab_search(queries)


# Single thread-pool so we never launch more than one browser at a time
_scraper_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="scraper")


async def scrape_and_upsert_live(queries: List[RouteQuery]) -> None:
    """
    Scrapes live availability from ConfirmTKT for a list of RouteQueries
    and upserts them into the database. No login required.

    Playwright is run in a separate thread with a ProactorEventLoop so
    that subprocess creation works on Windows.
    """
    if not queries or os.getenv("TESTING") == "1":
        return

    headless = os.getenv("SCRAPER_HEADLESS", "false").lower() == "true"
    max_tabs = int(os.getenv("SCRAPER_MAX_TABS", "6"))

    # Run Playwright in a worker thread with its own event loop
    loop = asyncio.get_running_loop()
    import logging
    log = logging.getLogger(__name__)
    log.info("Starting scrape for %d queries (headless=%s)", len(queries), headless)
    
    try:
        results = await loop.run_in_executor(
            _scraper_pool,
            _run_scraper_sync,
            queries,
            headless,
            max_tabs,
        )
        log.info("Scrape returned %d results", len(results))
    except Exception as e:
        import traceback
        log.error("Scraper crashed: %s\n%s", e, traceback.format_exc())
        results = []

    if results:
        if db_pool.closed:
            db_pool.open()
        with db_pool.connection() as conn:
            with conn.transaction():
                upsert_results(conn, results)
        log.info("Scraped and upserted %d availability records.", len(results))
    else:
        print("Scraper returned no results.")
