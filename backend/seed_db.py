from datetime import time
from pathlib import Path
from app.database import db_pool
from app.repositories.rail_repository import InMemoryRailRepository

def seed():
    # Initialize the in-memory repository to get the mock data
    repo = InMemoryRailRepository()
    stations = repo.list_stations()
    # To get segments, we access the protected _segments (just for seeding)
    segments = repo._segments

    # Collect unique trains from segments
    trains = {}
    for seg in segments:
        if seg.train_number not in trains:
            trains[seg.train_number] = {
                "number": seg.train_number,
                "name": seg.train_name,
                "train_type": "Superfast",
                "run_days": list(seg.run_days)
            }

    db_pool.open()
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # 1. Automatically apply schema if not already present
            schema_path = Path(__file__).parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
            
            # 2. Seed stations
            for st in stations:
                cur.execute(
                    "INSERT INTO stations (code, name, city, state, score, is_junction) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (code) DO NOTHING",
                    (st.code, st.name, st.city, st.state, st.score, st.is_junction)
                )
            
            # 3. Seed trains
            for t in trains.values():
                cur.execute(
                    "INSERT INTO trains (number, name, train_type, run_days) VALUES (%s, %s, %s, %s) ON CONFLICT (number) DO NOTHING",
                    (t["number"], t["name"], t["train_type"], t["run_days"])
                )
            
            # 4. Seed segments
            for seg in segments:
                cur.execute(
                    "SELECT 1 FROM train_segments WHERE train_number = %s AND from_station = %s AND to_station = %s AND class_code = %s",
                    (seg.train_number, seg.from_station, seg.to_station, seg.class_code)
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO train_segments 
                        (train_number, from_station, to_station, departure, arrival, duration_min, distance_km, fare, class_code, available_seats, run_days)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (seg.train_number, seg.from_station, seg.to_station, seg.departure, seg.arrival, 
                         seg.duration_min, seg.distance_km, seg.fare, seg.class_code, 0, list(seg.run_days))
                    )
        conn.commit()
    db_pool.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed()
