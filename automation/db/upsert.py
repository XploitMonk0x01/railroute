"""
automation/db/upsert.py
────────────────────────
Writes scraped AvailabilityResult objects into the RailRoute PostgreSQL
database.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, time

import psycopg

from scraper.models import AvailabilityResult

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Train-id resolver (cached per connection to avoid N+1 lookups)
# ──────────────────────────────────────────────────────────────

_train_id_cache: dict[str, int | None] = {}


def resolve_train_id(
    conn: psycopg.Connection, train_number: str, train_name: str
) -> int:
    """
    Look up the primary key `id` for a given train number.
    Inserts the train if it doesn't exist.
    """
    if train_number in _train_id_cache and _train_id_cache[train_number] is not None:
        return _train_id_cache[train_number]  # type: ignore

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM trains WHERE number = %s",
            (train_number,),
        )
        row = cur.fetchone()

        if row:
            tid = row[0]
        else:
            log.info("Inserting missing train: %s (%s)", train_number, train_name)
            cur.execute(
                "INSERT INTO trains (number, name) VALUES (%s, %s) RETURNING id",
                (train_number, train_name),
            )
            res = cur.fetchone()
            tid = res[0] if res else 0

    _train_id_cache[train_number] = tid
    return tid


# ──────────────────────────────────────────────────────────────
# seat_availability upsert
# ──────────────────────────────────────────────────────────────

_UPSERT_SEAT_AVAIL = """
INSERT INTO seat_availability (
    train_id,
    journey_date,
    class_code,
    from_station,
    to_station,
    available_seats,
    wl_number,
    status,
    quota,
    fare,
    fetched_at
)
VALUES (
    %(train_id)s,
    %(journey_date)s,
    %(class_code)s,
    %(from_station)s,
    %(to_station)s,
    %(available_seats)s,
    %(wl_number)s,
    %(status)s,
    %(quota)s,
    %(fare)s,
    %(fetched_at)s
)
ON CONFLICT (train_id, journey_date, class_code, from_station, to_station, quota)
DO UPDATE SET
    available_seats = EXCLUDED.available_seats,
    wl_number       = EXCLUDED.wl_number,
    status          = EXCLUDED.status,
    fare            = COALESCE(EXCLUDED.fare, seat_availability.fare),
    fetched_at      = EXCLUDED.fetched_at
"""


def upsert_results(
    conn: psycopg.Connection,
    results: Iterable[AvailabilityResult],
    *,
    also_update_segments: bool = True,
) -> tuple[int, int]:
    ok = 0
    skipped = 0

    with conn.cursor() as cur:
        for r in results:
            train_id = resolve_train_id(conn, r.train_number, r.train_name)

            cur.execute(
                _UPSERT_SEAT_AVAIL,
                {
                    "train_id":       train_id,
                    "journey_date":   r.journey_date,
                    "class_code":     r.class_code,
                    "from_station":   r.from_code,
                    "to_station":     r.to_code,
                    "available_seats": r.available_seats,
                    "wl_number":      r.wl_number,
                    "status":         r.status,
                    "quota":          r.quota,
                    "fare":           r.fare,
                    "fetched_at":     r.fetched_at,
                },
            )
            ok += 1

            if also_update_segments:
                _update_segment_seats(
                    conn,
                    train_id       = train_id,
                    train_number   = r.train_number,
                    from_station   = r.from_code,
                    to_station     = r.to_code,
                    class_code     = r.class_code,
                    available_seats= r.available_seats,
                    departure      = r.departure,
                    arrival        = r.arrival,
                    duration_min   = r.duration_min,
                    fare           = r.fare,
                    cur            = cur,
                )

    # Don't commit here! Let the caller manage the transaction.
    # Actually wait, in previous version it did conn.commit() here! 
    # But route_service.py's caller also wraps it in `with conn.transaction():`.
    # Let's not commit explicitly here.
    log.info("DB write complete: %d upserted, %d skipped.", ok, skipped)
    return ok, skipped


# ──────────────────────────────────────────────────────────────
# train_segments sync
# ──────────────────────────────────────────────────────────────

_UPDATE_SEGMENTS = """
UPDATE train_segments
SET    available_seats = %(seats)s
WHERE  train_number    = %(train_number)s
  AND  from_station    = %(from_station)s
  AND  to_station      = %(to_station)s
  AND  class_code      = %(class_code)s
"""

_INSERT_SEGMENT = """
INSERT INTO train_segments (
    train_number,
    from_station,
    to_station,
    class_code,
    departure,
    arrival,
    duration_min,
    available_seats,
    fare,
    distance_km,
    run_days
) VALUES (
    %(train_number)s,
    %(from_station)s,
    %(to_station)s,
    %(class_code)s,
    %(departure)s,
    %(arrival)s,
    %(duration_min)s,
    %(seats)s,
    %(fare)s,
    %(distance_km)s,
    %(run_days)s
)
"""


def _update_segment_seats(
    conn: psycopg.Connection,
    train_id:        int,
    train_number:    str,
    from_station:    str,
    to_station:      str,
    class_code:      str,
    available_seats: int,
    departure:       str,
    arrival:         str,
    duration_min:    int,
    fare:            float | None,
    cur: psycopg.Cursor,
) -> None:
    params = {
        "train_number":   train_number,
        "from_station":   from_station,
        "to_station":     to_station,
        "class_code":     class_code,
        "seats":          available_seats,
    }

    cur.execute(_UPDATE_SEGMENTS, params)
    
    if cur.rowcount == 0:
        log.info(
            "Inserting missing train_segment: %s %s→%s [%s]",
            train_number, from_station, to_station, class_code,
        )
        
        # convert 'HH:MM' string to datetime.time
        def parse_time(t_str: str) -> time:
            try:
                dt = datetime.strptime(t_str, "%H:%M")
                return dt.time()
            except Exception:
                return time(0, 0)
                
        cur.execute(_INSERT_SEGMENT, {
            "train_number": train_number,
            "from_station": from_station,
            "to_station": to_station,
            "class_code": class_code,
            "departure": parse_time(departure),
            "arrival": parse_time(arrival),
            "duration_min": duration_min,
            "seats": available_seats,
            "fare": fare if fare is not None else 0.0,
            "distance_km": 0,
            "run_days": [0, 1, 2, 3, 4, 5, 6],
        })
