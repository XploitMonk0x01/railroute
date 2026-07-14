from fastapi import APIRouter

from app.api.v1.routes import auth, health, search, stations, watchlist

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(stations.router, prefix="/stations", tags=["stations"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
