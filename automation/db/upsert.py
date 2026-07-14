"""
automation/db/upsert.py
────────────────────────
Writes scraped AvailabilityResult objects into the RailRoute PostgreSQL
database.

Two write paths
───────────────
1. seat_availability  — date-specific table that the plan specifies as the
   canonical store for real availability data.  Uses INSERT ... ON CONFLICT
   DO UPDATE so repeated scrapes are idempotent.

2. train_segments.available_seats — the column the graph engine currently reads
   when deciding whether a route is "available".  We sync this so the FastAPI
   /api/v1/search endpoint immediately returns real data without needing a
   graph rebuild.

Dependencies
────────────
• psycopg3 (same driver as the backend) — no extra imports needed.
• No ORM / no backend package imports so this module works standalone.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

import psycopg

from scraper.models import AvailabilityResult

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Train-id resolver (cached per connection to avoid N+1 lookups)
# ──────────────────────────────────────────────────────────────

_train_id_cache: dict[str, int | None] = {}


def resolve_train_id(
    conn: psycopg.Connection, train_number: str
) -> int | None:
    """
    Look up the primary key `id` for a given train number.
    Returns None if the train is not in the DB (logs a warning).
    Results are cached in-process for the lifetime of the scraper run.
    """
    if train_number in _train_id_cache:
        return _train_id_cache[train_number]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM trains WHERE number = %s",
            (train_number,),
        )
        row = cur.fetchone()

    tid = row[0] if row else None
    _train_id_cache[train_number] = tid

    if tid is None:
        log.warning(
            "Train %s not found in the trains table — skipping. "
            "Run seed_db.py or add this train manually.",
            train_number,
        )
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
    """
    Upsert a batch of AvailabilityResult rows into `seat_availability`.

    Parameters
    ----------
    conn                 : open psycopg3 connection (caller manages transaction)
    results              : iterable of scraped availability records
    also_update_segments : if True, also update train_segments.available_seats

    Returns
    -------
    (inserted_or_updated, skipped) counts
    """
    ok = 0
    skipped = 0

    with conn.cursor() as cur:
        for r in results:
            train_id = resolve_train_id(conn, r.train_number)
            if train_id is None:
                skipped += 1
                continue

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
                update_segment_seats(
                    conn,
                    train_number   = r.train_number,
                    from_station   = r.from_code,
                    to_station     = r.to_code,
                    class_code     = r.class_code,
                    available_seats= r.available_seats,
                    cur            = cur,
                )

    conn.commit()
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


def update_segment_seats(
    conn: psycopg.Connection,
    train_number:    str,
    from_station:    str,
    to_station:      str,
    class_code:      str,
    available_seats: int,
    *,
    cur: psycopg.Cursor | None = None,
) -> int:
    """
    Update `available_seats` in the train_segments table for matching rows.
    This keeps the graph engine's data in sync with fresh scrape results.

    Returns the number of rows updated (0 = segment not yet in DB).
    """
    params = {
        "train_number":   train_number,
        "from_station":   from_station,
        "to_station":     to_station,
        "class_code":     class_code,
        "seats":          available_seats,
    }

    if cur is not None:
        cur.execute(_UPDATE_SEGMENTS, params)
        updated = cur.rowcount
    else:
        with conn.cursor() as c:
            c.execute(_UPDATE_SEGMENTS, params)
            updated = c.rowcount
        conn.commit()

    if updated == 0:
        log.debug(
            "No train_segment found for %s %s→%s [%s] — "
            "seat count NOT synced to graph engine.",
            train_number, from_station, to_station, class_code,
        )
    return updated
