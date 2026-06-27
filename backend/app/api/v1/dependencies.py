from functools import lru_cache

from app.database import get_db_pool
from app.repositories.pg_rail_repository import PgRailRepository
from app.repositories.rail_repository import RailRepository
from app.services.route_service import RouteService
from app.services.station_service import StationService


@lru_cache
def get_rail_repository() -> RailRepository:
    return PgRailRepository(get_db_pool())


def get_route_service() -> RouteService:
    return RouteService(get_rail_repository())


def get_station_service() -> StationService:
    return StationService(get_rail_repository())
