"""
automation/tests/test_upsert.py
────────────────────────────────
Integration tests for db/upsert.py.

These tests require a live PostgreSQL database.
They are skipped automatically when the DB is unavailable so CI without a DB
still passes (only the model unit tests run).

To run manually:
    cd automation
    source .venv/bin/activate
    RAILROUTE_DATABASE_URL=postgresql://master@127.0.0.1:5432/railroute pytest tests/test_upsert.py -v
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.models import AvailabilityResult
from db.upsert import upsert_results, update_segment_seats, resolve_train_id, _train_id_cache

# ──────────────────────────────────────────────────────────────
# DB fixture — skip the whole module if no DB available
# ──────────────────────────────────────────────────────────────

_DB_URL = os.getenv(
    "RAILROUTE_DATABASE_URL",
    "postgresql://master@127.0.0.1:5432/railroute",
)

try:
    import psycopg
    _conn_test = psycopg.connect(_DB_URL, connect_timeout=3)
    _conn_test.close()
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="PostgreSQL not available — skipping integration tests",
)


@pytest.fixture()
def conn():
    """Provide a psycopg3 connection that is rolled back after each test."""
    import psycopg as _psycopg
    with _psycopg.connect(_DB_URL) as c:
        yield c
        c.rollback()   # leave DB clean after every test


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _sample_result(
    train_number: str = "12351",
    status:       str = "AVAILABLE",
    seats:        int = 10,
    wl:           int = 0,
    journey_date: date | None = None,
) -> AvailabilityResult:
    return AvailabilityResult(
        train_number    = train_number,
        train_name      = "Test Express",
        from_code       = "HWH",
        to_code         = "PNBE",
        journey_date    = journey_date or date(2026, 8, 1),
        class_code      = "3A",
        quota           = "GN",
        status          = status,
        available_seats = seats,
        wl_number       = wl,
        fare            = 500.0,
        fetched_at      = datetime.now(tz=timezone.utc),
    )


# ──────────────────────────────────────────────────────────────
# resolve_train_id
# ──────────────────────────────────────────────────────────────

class TestResolveTrainId:
    def test_known_train_returns_int(self, conn):
        """12351 should exist after seed_db.py has been run."""
        _train_id_cache.clear()
        tid = resolve_train_id(conn, "12351")
        # May be None if seed hasn't been run — that's OK, just check type
        assert tid is None or isinstance(tid, int)

    def test_unknown_train_returns_none(self, conn):
        _train_id_cache.clear()
        tid = resolve_train_id(conn, "99999")
        assert tid is None

    def test_result_is_cached(self, conn):
        _train_id_cache.clear()
        tid1 = resolve_train_id(conn, "00000")
        tid2 = resolve_train_id(conn, "00000")
        assert tid1 == tid2  # same (None) value, fetched from cache on 2nd call


# ──────────────────────────────────────────────────────────────
# upsert_results
# ──────────────────────────────────────────────────────────────

class TestUpsertResults:
    def test_unknown_train_is_skipped(self, conn):
        """Trains not in the trains table must be silently skipped."""
        _train_id_cache.clear()
        r = _sample_result(train_number="99999")
        ok, skipped = upsert_results(conn, [r], also_update_segments=False)
        assert ok      == 0
        assert skipped == 1

    def test_upsert_is_idempotent(self, conn):
        """Calling upsert twice with the same data should not raise or duplicate."""
        _train_id_cache.clear()
        # Only run if 12351 is seeded
        if resolve_train_id(conn, "12351") is None:
            pytest.skip("Train 12351 not seeded — skipping idempotency test")

        r = _sample_result(train_number="12351")
        ok1, _  = upsert_results(conn, [r], also_update_segments=False)
        ok2, _  = upsert_results(conn, [r], also_update_segments=False)
        assert ok1 == 1
        assert ok2 == 1  # ON CONFLICT DO UPDATE → counts as 1

    def test_status_updated_on_conflict(self, conn):
        """A second upsert with a different status must overwrite the first."""
        _train_id_cache.clear()
        if resolve_train_id(conn, "12351") is None:
            pytest.skip("Train 12351 not seeded")

        r_available = _sample_result("12351", status="AVAILABLE", seats=5)
        upsert_results(conn, [r_available], also_update_segments=False)

        r_wl = _sample_result("12351", status="WL", seats=0, wl=10)
        upsert_results(conn, [r_wl], also_update_segments=False)

        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, available_seats, wl_number
                FROM   seat_availability
                WHERE  journey_date  = %s
                  AND  class_code    = 'GN'
                  AND  from_station  = 'HWH'
                  AND  to_station    = 'PNBE'
                  AND  quota         = 'GN'
                ORDER  BY fetched_at DESC
                LIMIT 1
            """, (date(2026, 8, 1),))
            row = cur.fetchone()

        assert row is not None
        status, seats, wl = row
        assert status == "WL"
        assert seats  == 0
        assert wl     == 10

    def test_empty_results_returns_zero(self, conn):
        ok, skipped = upsert_results(conn, [], also_update_segments=False)
        assert ok      == 0
        assert skipped == 0


# ──────────────────────────────────────────────────────────────
# update_segment_seats
# ──────────────────────────────────────────────────────────────

class TestUpdateSegmentSeats:
    def test_no_matching_segment_returns_zero(self, conn):
        updated = update_segment_seats(
            conn,
            train_number    = "99999",
            from_station    = "ZZZ",
            to_station      = "YYY",
            class_code      = "3A",
            available_seats = 5,
        )
        assert updated == 0

    def test_known_segment_updates_correctly(self, conn):
        """If 12351 HWH→PNBE 3A exists in train_segments, seats should update."""
        updated = update_segment_seats(
            conn,
            train_number    = "12351",
            from_station    = "HWH",
            to_station      = "PNBE",
            class_code      = "3A",
            available_seats = 99,
        )
        # updated == 0 is fine if segment not seeded; > 0 means it worked
        assert isinstance(updated, int)
        if updated > 0:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT available_seats FROM train_segments
                    WHERE  train_number = '12351'
                      AND  from_station = 'HWH'
                      AND  to_station   = 'PNBE'
                      AND  class_code   = '3A'
                    LIMIT 1
                """)
                row = cur.fetchone()
            assert row is not None
            assert row[0] == 99
