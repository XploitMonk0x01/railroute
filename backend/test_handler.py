import asyncio
import logging
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "automation"))

from scraper.models import RouteQuery
from scraper.irctc_client import IRCTCClient

logging.basicConfig(level=logging.INFO)

async def test():
    query = RouteQuery(from_code="NDLS", to_code="HW", date=datetime.date(2026, 9, 30), class_code="3A")
    async with IRCTCClient(headless=True) as client:
        results = await client.check_availability(query)
        print(f"Got {len(results)} results")

if __name__ == "__main__":
    asyncio.run(test())
