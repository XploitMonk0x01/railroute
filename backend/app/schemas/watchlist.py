from datetime import date
from pydantic import BaseModel, Field


class WatchlistCreateRequest(BaseModel):
    source_code: str = Field(min_length=2, max_length=10)
    destination_code: str = Field(min_length=2, max_length=10)
    journey_date: date
    preferred_class: str | None = None
    max_budget: float | None = Field(default=None, gt=0)
    notify_on: list[str] = Field(default_factory=lambda: ["AVAILABLE"])


class WatchlistEntryResponse(BaseModel):
    id: int
    source_code: str
    destination_code: str
    journey_date: date
    preferred_class: str | None
    max_budget: float | None
    notify_on: list[str]
    is_active: bool
    created_at: str
