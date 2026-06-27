from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.graph import rail_graph
from app.database import db_pool
from app.repositories.pg_rail_repository import PgRailRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: open the database connection pool
    db_pool.open()
    
    # Build in-memory NetworkX graph for routing
    print("Building RailGraph from database...")
    repo = PgRailRepository(db_pool)
    stations = repo.list_stations()
    segments = repo.list_all_segments()
    rail_graph.build(stations, segments)
    print(f"RailGraph built with {rail_graph.G.number_of_nodes()} stations and {rail_graph.G.number_of_edges()} segments.")
    
    yield
    
    # Shutdown: close the database connection pool
    db_pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.api_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
