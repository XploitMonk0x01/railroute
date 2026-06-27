from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_search_route_serializes_aliased_fields() -> None:
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