from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_route_service
from app.schemas.search import SearchRequest, SearchResponse
from app.services.route_service import RouteService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search_routes(
    request: SearchRequest,
    route_service: RouteService = Depends(get_route_service),
) -> SearchResponse:
    try:
        return route_service.search(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
