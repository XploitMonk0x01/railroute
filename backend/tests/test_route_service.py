from datetime import date, time

import pytest

from app.models.rail import Station, TrainSegment
from app.core.graph import rail_graph
from app.repositories.rail_repository import InMemoryRailRepository
from app.schemas.search import SearchRequest
from app.services.route_service import RouteService


class StaticRailRepository(InMemoryRailRepository):
    def __init__(self, stations: list[Station], segments: list[TrainSegment]) -> None:
        self._stations = stations
        self._segments = segments


def route_signature(route) -> tuple[tuple[str, str, str], ...]:
    return tuple((segment.train_number, segment.from_station, segment.to_station) for segment in route.segments)


def test_search_returns_alternative_when_direct_train_has_no_seats() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    request = SearchRequest(
        source="ADI",
        destination="NDLS",
        date=date(2026, 6, 10),
        constraints={"max_transfers": 2, "max_wait_min": 240},
    )

    response = service.search(request)

    assert response.direct_available is False
    assert response.alternatives
    assert response.alternatives[0].segments[0].from_station == "ADI"
    assert response.alternatives[0].segments[-1].to_station == "NDLS"


def test_search_rejects_same_source_and_destination() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    request = SearchRequest(source="ADI", destination="ADI", date=date(2026, 6, 10))

    with pytest.raises(ValueError, match="source and destination"):
        service.search(request)


def test_search_enforces_max_transfers() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    request = SearchRequest(
        source="ADI",
        destination="NDLS",
        date=date(2026, 6, 10),
        constraints={"max_transfers": 1, "max_wait_min": 240},
    )

    response = service.search(request)

    assert response.alternatives
    assert all(route.transfer_count <= 1 for route in response.alternatives)


def test_search_enforces_max_wait_min_on_transfer_waits_only() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    request = SearchRequest(
        source="ADI",
        destination="BRC",
        date=date(2026, 6, 10),
        constraints={"max_wait_min": 1},
    )

    response = service.search(request)

    assert response.direct_available is True
    assert response.direct_train is not None
    assert response.direct_train.to_station == "BRC"


def test_search_enforces_max_budget() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    request = SearchRequest(
        source="ADI",
        destination="NDLS",
        date=date(2026, 6, 10),
        constraints={"max_budget": 900},
    )

    response = service.search(request)

    assert response.alternatives
    assert all(route.total_fare <= 900 for route in response.alternatives)


def test_search_avoids_cyclic_routes() -> None:
    rail_graph.G.clear()
    stations = [
        Station("SRC", "Source", "Source City", "State", 50, False),
        Station("MID", "Midpoint", "Mid City", "State", 60, True),
        Station("DST", "Destination", "Dest City", "State", 70, False),
    ]
    daily = frozenset(range(7))
    segments = [
        TrainSegment("10001", "Loop Line", "SRC", "MID", time(8, 0), time(9, 0), 60, 50, 100, "3A", 10, daily),
        TrainSegment("10002", "Loop Back", "MID", "SRC", time(9, 30), time(10, 30), 60, 50, 100, "3A", 10, daily),
        TrainSegment("10003", "Final Hop", "MID", "DST", time(10, 45), time(11, 30), 45, 40, 80, "3A", 10, daily),
    ]
    service = RouteService(StaticRailRepository(stations, segments))
    request = SearchRequest(
        source="SRC",
        destination="DST",
        date=date(2026, 6, 10),
        constraints={"max_transfers": 3, "max_wait_min": 240},
    )

    response = service.search(request)

    assert response.alternatives
    assert all(len({segment.from_station for segment in route.segments} | {route.segments[-1].to_station}) == len(route.segments) + 1 for route in response.alternatives)


def test_search_scores_change_with_filter_preset() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    base_request = {
        "source": "ADI",
        "destination": "NDLS",
        "date": date(2026, 6, 10),
        "constraints": {"max_transfers": 2, "max_wait_min": 240},
    }

    fastest = service.search(SearchRequest(**base_request, filter_preset="fastest"))
    cheapest = service.search(SearchRequest(**base_request, filter_preset="cheapest"))
    best_availability = service.search(SearchRequest(**base_request, filter_preset="best_availability"))

    fastest_scores = {route_signature(route): route.score for route in fastest.alternatives}
    cheapest_scores = {route_signature(route): route.score for route in cheapest.alternatives}
    availability_scores = {route_signature(route): route.score for route in best_availability.alternatives}

    common_signatures = set(fastest_scores) & set(cheapest_scores) & set(availability_scores)
    assert common_signatures
    assert any(
        fastest_scores[signature] != cheapest_scores[signature]
        or fastest_scores[signature] != availability_scores[signature]
        for signature in common_signatures
    )


def test_hwh_to_pnbe_returns_alternatives_when_direct_ticket_unavailable() -> None:
    rail_graph.G.clear()
    service = RouteService(InMemoryRailRepository())
    request = SearchRequest(
        source="HWH",
        destination="PNBE",
        date=date(2026, 6, 28),
        class_code="3A",
        constraints={"max_transfers": 2, "max_wait_min": 240},
    )

    response = service.search(request)

    assert response.direct_available is False
    assert response.direct_train is not None
    assert response.direct_train.from_station == "HWH"
    assert response.direct_train.to_station == "PNBE"
    assert response.direct_train.availability == "WL"
    assert response.alternatives
    assert all(route.segments[0].from_station == "HWH" for route in response.alternatives)
    assert all(route.segments[-1].to_station == "PNBE" for route in response.alternatives)
    assert all(route.transfer_count >= 1 for route in response.alternatives)
