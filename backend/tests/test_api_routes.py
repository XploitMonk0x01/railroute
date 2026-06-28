from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_rail_repository
from app.core.graph import rail_graph
from app.main import app
from app.repositories.rail_repository import InMemoryRailRepository


client = TestClient(app)
app.dependency_overrides[get_rail_repository] = lambda: InMemoryRailRepository()


def test_search_route_serializes_aliased_fields() -> None:
    rail_graph.G.clear()
    response = client.post(
        "/api/v1/search",
        json={
            "source": "ADI",
            "destination": "NDLS",
            "date": "2026-06-10",
            "filter_preset": "fastest",
            "constraints": {"max_transfers": 2, "max_wait_min": 240},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"direct_available", "direct_train", "alternatives", "generated_at"}
    assert payload["direct_train"]["from"] == "ADI"
    assert payload["direct_train"]["to"] == "NDLS"
    assert payload["alternatives"]
    assert payload["alternatives"][0]["segments"][0]["from"] == "ADI"


def test_search_route_rejects_same_station() -> None:
    rail_graph.G.clear()
    response = client.post(
        "/api/v1/search",
        json={
            "source": "ADI",
            "destination": "ADI",
            "date": "2026-06-10",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "source and destination must be different"


def test_station_search_matches_code_city_and_name() -> None:
    assert client.get("/api/v1/stations?q=NDLS").status_code == 200
    assert client.get("/api/v1/stations?q=Ahmedabad").status_code == 200
    assert client.get("/api/v1/stations?q=Vadodara Junction").status_code == 200

    by_code = client.get("/api/v1/stations?q=NDLS").json()
    by_city = client.get("/api/v1/stations?q=Ahmedabad").json()
    by_name = client.get("/api/v1/stations?q=Vadodara Junction").json()

    assert by_code[0]["code"] == "NDLS"
    assert by_city[0]["code"] == "ADI"
    assert by_name[0]["code"] == "BRC"


def test_health_route_returns_status_and_version() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "RailRoute AI"
    assert payload["version"] == "0.1.0"


def test_hwh_to_pnbe_search_returns_no_direct_ticket_with_alternatives() -> None:
    rail_graph.G.clear()
    response = client.post(
        "/api/v1/search",
        json={
            "source": "HWH",
            "destination": "PNBE",
            "date": "2026-06-28",
            "class": "3A",
            "constraints": {"max_transfers": 2, "max_wait_min": 240},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["direct_available"] is False
    assert payload["direct_train"]["from"] == "HWH"
    assert payload["direct_train"]["to"] == "PNBE"
    assert payload["direct_train"]["availability"] == "WL"
    assert payload["alternatives"]
    assert payload["alternatives"][0]["segments"][0]["from"] == "HWH"
    assert payload["alternatives"][0]["segments"][-1]["to"] == "PNBE"
