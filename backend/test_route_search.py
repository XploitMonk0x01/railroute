import asyncio
from datetime import date
from app.repositories.pg_rail_repository import PgRailRepository
from app.services.route_service import RouteService
from app.database import db_pool
from app.schemas.search import SearchRequest, SearchConstraints

async def main():
    db_pool.open()
    try:
        repo = PgRailRepository(db_pool)
        service = RouteService(repo)
        print("Finding routes from BRC to PNBE on 2026-07-31...")
        request = SearchRequest(
            source="BRC", 
            destination="PNBE", 
            date=date(2026, 7, 31), 
            class_code=None,
            constraints=SearchConstraints(max_transfers=3, max_wait_min=1440)
        )
        import os
        print("TESTING env:", os.getenv("TESTING"))
        candidates = service._find_routes(request, ignore_availability=True)
        print("Candidates count:", len(candidates))
        response = await service.search(request)
        routes = response.alternatives
        print(f"Found {len(routes)} alternatives.")
        for i, route in enumerate(routes):
            print(f"\nRoute {i+1} (Score: {route.score}):")
            for seg in route.segments:
                print(f"  {seg.train_number} ({seg.train_name}): {seg.from_station} -> {seg.to_station}")
    finally:
        db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())
