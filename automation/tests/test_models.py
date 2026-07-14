"""
automation/tests/test_models.py
────────────────────────────────
Unit tests for scraper.models — no Playwright, no DB required.
"""

from datetime import date, datetime

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.models import (
    AvailabilityResult,
    RouteQuery,
    VALID_STATUSES,
    parse_availability_text,
)


# ──────────────────────────────────────────────────────────────
# RouteQuery
# ──────────────────────────────────────────────────────────────

class TestRouteQuery:
    def test_codes_normalised_to_upper(self):
        q = RouteQuery("hwh", "pnbe", date(2026, 7, 20), "3a", "gn")
        assert q.from_code  == "HWH"
        assert q.to_code    == "PNBE"
        assert q.class_code == "3A"
        assert q.quota      == "GN"



    def test_str_representation(self):
        q = RouteQuery("HWH", "PNBE", date(2026, 7, 20), "3A")
        s = str(q)
        assert "HWH" in s and "PNBE" in s and "3A" in s

    def test_default_quota_is_gn(self):
        q = RouteQuery("HWH", "PNBE", date(2026, 7, 20), "3A")
        assert q.quota == "GN"

    def test_frozen_immutability(self):
        q = RouteQuery("HWH", "PNBE", date(2026, 7, 20), "3A")
        with pytest.raises((AttributeError, TypeError)):
            q.from_code = "ASN"  # type: ignore[misc]

    def test_whitespace_stripped(self):
        q = RouteQuery("  HWH  ", "  PNBE  ", date(2026, 7, 20), "  3A  ")
        assert q.from_code  == "HWH"
        assert q.class_code == "3A"


# ──────────────────────────────────────────────────────────────
# parse_availability_text
# ──────────────────────────────────────────────────────────────

class TestParseAvailabilityText:
    @pytest.mark.parametrize("raw,expected", [
        ("AVAILABLE - 12",  ("AVAILABLE", 12, 0)),
        ("AVAILABLE-5",     ("AVAILABLE",  5, 0)),
        ("AVAILABLE",       ("AVAILABLE",  0, 0)),
        ("Available 8",     ("AVAILABLE",  8, 0)),
    ])
    def test_available(self, raw, expected):
        assert parse_availability_text(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("WL# 45",       ("WL", 0, 45)),
        ("WL 3",         ("WL", 0,  3)),
        ("WL#100",       ("WL", 0, 100)),
        ("WL-22",        ("WL", 0, 22)),
    ])
    def test_waitlist(self, raw, expected):
        assert parse_availability_text(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("RAC 8",  ("RAC", 8, 0)),
        ("RAC-3",  ("RAC", 3, 0)),
        ("RAC",    ("RAC", 0, 0)),
    ])
    def test_rac(self, raw, expected):
        assert parse_availability_text(raw) == expected

    @pytest.mark.parametrize("raw", ["REGRET", "REGRET/WL", "NO VACANCY", ""])
    def test_regret_and_unknown(self, raw):
        status, seats, wl = parse_availability_text(raw)
        assert status == "REGRET"
        assert seats  == 0
        assert wl     == 0

    def test_case_insensitive(self):
        status, seats, _ = parse_availability_text("available - 7")
        assert status == "AVAILABLE"
        assert seats  == 7


# ──────────────────────────────────────────────────────────────
# AvailabilityResult
# ──────────────────────────────────────────────────────────────

def _make_result(**kwargs) -> AvailabilityResult:
    defaults = dict(
        train_number    = "12351",
        train_name      = "Howrah Patna Express",
        from_code       = "HWH",
        to_code         = "PNBE",
        journey_date    = date(2026, 7, 20),
        class_code      = "3A",
        quota           = "GN",
        status          = "AVAILABLE",
        available_seats = 12,
        wl_number       = 0,
        fare            = 750.0,
        fetched_at      = datetime(2026, 7, 13, 5, 30),
    )
    defaults.update(kwargs)
    return AvailabilityResult(**defaults)


class TestAvailabilityResult:
    def test_is_bookable_when_available_and_seats(self):
        r = _make_result(status="AVAILABLE", available_seats=5)
        assert r.is_bookable is True

    def test_not_bookable_when_available_but_zero_seats(self):
        r = _make_result(status="AVAILABLE", available_seats=0)
        assert r.is_bookable is False

    def test_not_bookable_when_waitlisted(self):
        r = _make_result(status="WL", available_seats=0, wl_number=10)
        assert r.is_bookable is False

    def test_not_bookable_when_regret(self):
        r = _make_result(status="REGRET")
        assert r.is_bookable is False

    def test_unknown_status_normalised_to_regret(self):
        r = _make_result(status="UNKNOWN_STATUS")
        assert r.status == "REGRET"

    def test_codes_normalised_to_upper(self):
        r = _make_result(from_code="hwh", to_code="pnbe", class_code="3a", quota="gn")
        assert r.from_code  == "HWH"
        assert r.to_code    == "PNBE"
        assert r.class_code == "3A"
        assert r.quota      == "GN"

    def test_str_includes_train_and_route(self):
        r = _make_result()
        s = str(r)
        assert "12351" in s
        assert "HWH" in s
        assert "PNBE" in s

    def test_rac_str_representation(self):
        r = _make_result(status="RAC", available_seats=3)
        s = str(r)
        assert "RAC" in s

    def test_wl_str_representation(self):
        r = _make_result(status="WL", wl_number=42, available_seats=0)
        s = str(r)
        assert "WL#42" in s

    def test_fare_can_be_none(self):
        r = _make_result(fare=None)
        assert r.fare is None

    def test_all_valid_statuses_accepted(self):
        for s in VALID_STATUSES:
            r = _make_result(status=s)
            assert r.status == s
