from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_station_service
from app.schemas.station import StationResponse
from app.services.station_service import StationService

router = APIRouter()


@router.get("", response_model=list[StationResponse])
def search_stations(
    q: str = Query(default="", max_length=100),
    station_service: StationService = Depends(get_station_service),
) -> list[StationResponse]:
    return station_service.search(q)


@router.get("/top-junctions", response_model=list[StationResponse])
def top_junctions(
    station_service: StationService = Depends(get_station_service),
) -> list[StationResponse]:
    return station_service.top_junctions()
