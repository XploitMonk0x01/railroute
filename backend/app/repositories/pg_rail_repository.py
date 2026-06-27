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
