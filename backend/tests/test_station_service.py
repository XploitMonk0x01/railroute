from app.repositories.rail_repository import InMemoryRailRepository
from app.services.station_service import StationService


def test_station_search_matches_code_and_city() -> None:
    service = StationService(InMemoryRailRepository())

    by_code = service.search("NDLS")
    by_city = service.search("Ahmedabad")

    assert by_code[0].code == "NDLS"
    assert by_city[0].code == "ADI"
