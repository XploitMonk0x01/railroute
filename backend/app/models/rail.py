from dataclasses import dataclass
from datetime import date, time
from typing import Any


@dataclass(frozen=True)
class Station:
    code: str
    name: str
    city: str
    state: str
    score: int = 0
    is_junction: bool = False
    id: int | None = None
    zone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    train_count: int = 0
    created_at: Any | None = None
    updated_at: Any | None = None


@dataclass(frozen=True)
class Train:
    number: str
    name: str
    train_type: str
    run_days: frozenset[int]


@dataclass(frozen=True)
class TrainSegment:
    train_number: str
    train_name: str
    from_station: str
    to_station: str
    departure: time
    arrival: time
    duration_min: int
    distance_km: int
    fare: float
    class_code: str
    available_seats: int
    run_days: frozenset[int]

    def runs_on(self, journey_date: date) -> bool:
        return journey_date.weekday() in self.run_days
