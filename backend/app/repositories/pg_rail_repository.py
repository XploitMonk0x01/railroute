from __future__ import annotations

from datetime import date, datetime

from psycopg.rows import class_row
from psycopg_pool import ConnectionPool

from app.models.rail import Station, TrainSegment
from app.repositories.rail_repository import RailRepository


class PgRailRepository(RailRepository):
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def list_stations(self) -> list[Station]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=class_row(Station)) as cur:
                cur.execute("SELECT * FROM stations ORDER BY score DESC")
                return cur.fetchall()

    def search_stations(self, query: str) -> list[Station]:
        normalized = query.strip().lower()
        if not normalized:
            with self._pool.connection() as conn:
                with conn.cursor(row_factory=class_row(Station)) as cur:
                    cur.execute("SELECT * FROM stations ORDER BY score DESC LIMIT 10")
                    return cur.fetchall()
        
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=class_row(Station)) as cur:
                cur.execute("""
                    SELECT * FROM stations 
                    WHERE LOWER(code) LIKE %s OR LOWER(name) LIKE %s OR LOWER(city) LIKE %s 
                    ORDER BY score DESC
                """, (f"%{normalized}%", f"%{normalized}%", f"%{normalized}%"))
                return cur.fetchall()

    def list_segments_from(self, station_code: str) -> list[TrainSegment]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=class_row(TrainSegment)) as cur:
                cur.execute("""
                    SELECT 
                        train_number, 
                        t.name as train_name, 
                        from_station, 
                        to_station, 
                        departure, 
                        arrival, 
                        duration_min, 
                        distance_km, 
                        fare, 
                        class_code, 
                        available_seats, 
                        ts.run_days
                    FROM train_segments ts
                    JOIN trains t ON ts.train_number = t.number
                    WHERE from_station = %s
                """, (station_code.upper(),))
                return cur.fetchall()

    def list_direct_segments(self, source_code: str, destination_code: str) -> list[TrainSegment]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=class_row(TrainSegment)) as cur:
                cur.execute("""
                    SELECT 
                        train_number, 
                        t.name as train_name, 
                        from_station, 
                        to_station, 
                        departure, 
                        arrival, 
                        duration_min, 
                        distance_km, 
                        fare, 
                        class_code, 
                        available_seats, 
                        ts.run_days
                    FROM train_segments ts
                    JOIN trains t ON ts.train_number = t.number
                    WHERE from_station = %s AND to_station = %s
                """, (source_code.upper(), destination_code.upper()))
                return cur.fetchall()

    def list_all_segments(self) -> list[TrainSegment]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=class_row(TrainSegment)) as cur:
                cur.execute("""
                    SELECT 
                        train_number, 
                        t.name as train_name, 
                        from_station, 
                        to_station, 
                        departure, 
                        arrival, 
                        duration_min, 
                        distance_km, 
                        fare, 
                        class_code, 
                        available_seats, 
                        ts.run_days
                    FROM train_segments ts
                    JOIN trains t ON ts.train_number = t.number
                """)
                return cur.fetchall()

    # ──────────────────────────────────────────────────────────
    # Availability write methods (called by automation scraper)
    # ──────────────────────────────────────────────────────────

    def upsert_seat_availability(
        self,
        train_number:    str,
        journey_date:    date,
        class_code:      str,
        from_station:    str,
        to_station:      str,
        available_seats: int,
        wl_number:       int,
        status:          str,
        quota:           str  = "GN",
        fare:            float | None = None,
        fetched_at:      datetime | None = None,
    ) -> None:
        """
        Upsert a single availability record into `seat_availability`.
        Resolves train_number → train_id internally.
        Skips silently if the train is not in the `trains` table.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM trains WHERE number = %s", (train_number,))
                row = cur.fetchone()
                if row is None:
                    return  # train not seeded — skip
                train_id = row[0]

                cur.execute("""
                    INSERT INTO seat_availability (
                        train_id, journey_date, class_code,
                        from_station, to_station,
                        available_seats, wl_number, status,
                        quota, fare, fetched_at
                    )
                    VALUES (
                        %(train_id)s, %(journey_date)s, %(class_code)s,
                        %(from_station)s, %(to_station)s,
                        %(available_seats)s, %(wl_number)s, %(status)s,
                        %(quota)s, %(fare)s, %(fetched_at)s
                    )
                    ON CONFLICT (train_id, journey_date, class_code, from_station, to_station, quota)
                    DO UPDATE SET
                        available_seats = EXCLUDED.available_seats,
                        wl_number       = EXCLUDED.wl_number,
                        status          = EXCLUDED.status,
                        fare            = COALESCE(EXCLUDED.fare, seat_availability.fare),
                        fetched_at      = EXCLUDED.fetched_at
                """, {
                    "train_id":       train_id,
                    "journey_date":   journey_date,
                    "class_code":     class_code,
                    "from_station":   from_station,
                    "to_station":     to_station,
                    "available_seats": available_seats,
                    "wl_number":      wl_number,
                    "status":         status,
                    "quota":          quota,
                    "fare":           fare,
                    "fetched_at":     fetched_at or datetime.utcnow(),
                })

    def update_segment_seats(
        self,
        train_number:    str,
        from_station:    str,
        to_station:      str,
        class_code:      str,
        available_seats: int,
    ) -> int:
        """
        Sync `train_segments.available_seats` after a scrape so the graph
        engine immediately reflects real availability.  Returns rows updated.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE train_segments
                    SET    available_seats = %(seats)s
                    WHERE  train_number    = %(train_number)s
                      AND  from_station    = %(from_station)s
                      AND  to_station      = %(to_station)s
                      AND  class_code      = %(class_code)s
                """, {
                    "train_number": train_number,
                    "from_station": from_station,
                    "to_station":   to_station,
                    "class_code":   class_code,
                    "seats":        available_seats,
                })
                return cur.rowcount
