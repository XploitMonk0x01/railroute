from app.repositories.rail_repository import RailRepository
from app.schemas.station import StationResponse


class StationService:
    def __init__(self, rail_repository: RailRepository) -> None:
        self._rail_repository = rail_repository

    def search(self, query: str) -> list[StationResponse]:
        return [StationResponse(**station.__dict__) for station in self._rail_repository.search_stations(query)]

    def top_junctions(self, limit: int = 10) -> list[StationResponse]:
        stations = [
            station
            for station in self._rail_repository.list_stations()
            if station.is_junction
        ]
        return [StationResponse(**station.__dict__) for station in stations[:limit]]
