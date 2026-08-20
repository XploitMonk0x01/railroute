"""
Quick smoke test for the ConfirmTkt scraper.
Run with: python test_confirmtkt_scraper.py
"""
import asyncio
import sys
import os
from datetime import date
from pathlib import Path

# Add automation to path
sys.path.insert(0, str(Path(__file__).parent.parent / "automation"))

from scraper.irctc_client import IRCTCClient
from scraper.models import RouteQuery


async def main() -> None:
    query = RouteQuery(
        from_code="BRC",
        to_code="NDLS",
        date=date(2026, 9, 30),
        class_code="3A",
    )

    print(f"Scraping ConfirmTkt for {query} …\n")

    async with IRCTCClient(headless=True, max_tabs=1) as client:
        results = await client.check_availability(query)

    if not results:
        print("No results returned.")
    else:
        print(f"Found {len(results)} result(s):\n")
        for r in results:
            print(
                f"  {r.train_number:>6} | {r.train_name:<35} | "
                f"{r.class_code:<3} | {r.status:<15} | "
                f"seats={r.available_seats:>3} | "
                f"fare=₹{r.fare or '?'}"
            )


if __name__ == "__main__":
    asyncio.run(main())
