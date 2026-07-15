import asyncio
import logging
from automation.scraper.models import RouteQuery
from automation.scraper.irctc_client import IRCTCClient

logging.basicConfig(level=logging.INFO)

import datetime
async def test():
    query = RouteQuery(from_code="NDLS", to_code="HW", date=datetime.date(2026, 8, 23), class_code="3A")
    async with IRCTCClient(headless=True) as client:
        results = await client.check_availability(query)
        print(f"Got {len(results)} results")

asyncio.run(test())
