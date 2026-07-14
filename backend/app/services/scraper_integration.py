import sys
import os
import asyncio
from datetime import date
from typing import List
from pathlib import Path

# Load .env file so os.getenv() can read settings
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

from scraper.confirmtkt_client import ConfirmTktClient
from scraper.models import RouteQuery
from db.upsert import upsert_results
from app.database import db_pool


async def scrape_and_upsert_live(queries: List[RouteQuery]) -> None:
    """
    Scrapes live availability for a list of RouteQueries from ConfirmTkt
    and upserts them into the database.

    ConfirmTkt requires no login — it publicly exposes cached IRCTC
    availability data, making it far more reliable than direct IRCTC scraping.
    """
    if not queries or os.getenv("TESTING") == "1":
        return

    headless = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
    max_tabs = int(os.getenv("SCRAPER_MAX_TABS", "4"))

    async with ConfirmTktClient(headless=headless, max_tabs=max_tabs) as client:
        results = await client.multi_tab_search(queries)

    if results:
        with db_pool.connection() as conn:
            upsert_results(conn, results)
        print(f"Scraped and upserted {len(results)} availability records from ConfirmTkt.")
    else:
        print("ConfirmTkt scraper returned no results.")
