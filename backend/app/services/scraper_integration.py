import sys
import os
import asyncio
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
from scraper.models import RouteQuery
from db.upsert import upsert_results
from app.database import db_pool


async def scrape_and_upsert_live(queries: List[RouteQuery]) -> None:
    """
    Scrapes live availability for a list of RouteQueries and upserts them into the database.
    """
    if not queries or os.getenv("TESTING") == "1":
        return

    # Read credentials and config from environment
    irctc_user = os.getenv("IRCTC_USER", "")
    irctc_pass = os.getenv("IRCTC_PASS", "")
    headless = os.getenv("SCRAPER_HEADLESS", "false").lower() == "true"
    max_tabs = int(os.getenv("SCRAPER_MAX_TABS", "6"))

    if not irctc_user or not irctc_pass:
        print("Warning: IRCTC_USER or IRCTC_PASS not set. Scraper may fail if login is required.")

    async with IRCTCClient(headless=headless, max_tabs=max_tabs) as client:
        if irctc_user and irctc_pass:
            await client.login(irctc_user, irctc_pass)
        
        results = await client.multi_tab_search(queries)
    
    if results:
        with db_pool.connection() as conn:
            upsert_results(conn, results)
        print(f"Scraped and upserted {len(results)} availability records.")
    else:
        print("Scraper returned no results.")
