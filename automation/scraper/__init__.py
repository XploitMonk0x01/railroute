"""automation/scraper/__init__.py"""
from .models import AvailabilityResult, RouteQuery, parse_availability_text
from .irctc_client import IRCTCClient

__all__ = [
    "IRCTCClient",
    "RouteQuery",
    "AvailabilityResult",
    "parse_availability_text",
]
