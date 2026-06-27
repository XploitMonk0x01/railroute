from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


ClassCode = Literal["1A", "2A", "3A", "SL", "CC", "EC"]
FilterPreset = Literal["default", "fastest", "cheapest", "least_transfers", "best_availability"]


class SearchConstraints(BaseModel):
    max_transfers: int = Field(default=2, ge=0, le=5)
    max_wait_min: int = Field(default=240, ge=0, le=1440)
    max_budget: float | None = Field(default=None, gt=0)


class SearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(min_length=2, max_length=10)
    destination: str = Field(min_length=2, max_length=10)
    date: date
    class_code: ClassCode | None = Field(default=None, alias="class")
    filter_preset: FilterPreset = settings.default_filter_preset
    constraints: SearchConstraints = Field(
        default_factory=lambda: SearchConstraints(
            max_transfers=settings.default_max_transfers,
            max_wait_min=settings.default_max_wait_min,
        )
    )

    @field_validator("source", "destination")
    @classmethod
    def normalize_station_code(cls, value: str) -> str:
        return value.strip().upper()


class RouteSegmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    train_number: str
    train_name: str
    train_type: str = "Superfast"
    from_station: str = Field(alias="from")
    from_name: str = ""
    to_station: str = Field(alias="to")
    to_name: str = ""
    departure: time
    arrival: time
    duration_min: int
    distance_km: int = 0
    wait_min: int
    is_transfer: bool = False
    day: int = 1
    class_code: str = Field(alias="class")
    fare: float
    availability: str


class RouteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    route_id: str
    score: float
    total_time_min: int
    total_fare: float
    transfer_count: int
    total_wait_min: int = Field(alias="wait_min")
    segments: list[RouteSegmentResponse]


class SearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    direct_available: bool
    direct_train: RouteSegmentResponse | None
    alternatives: list[RouteResponse]
    generated_at: datetime
