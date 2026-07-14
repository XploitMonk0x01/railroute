"""
automation/scraper/models.py
────────────────────────────
Pure dataclasses for the scraper layer.  No database, no ORM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


# ──────────────────────────────────────────────────────────────
# Input
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RouteQuery:
    """A single availability lookup request."""

    from_code:  str          # e.g. "HWH"
    to_code:    str          # e.g. "PNBE"
    date:       date         # journey date
    class_code: str          # 1A | 2A | 3A | SL | CC | EC
    quota:      str = "GN"  # GN | TQ | PT | LD | SS …

    def __post_init__(self) -> None:
        object.__setattr__(self, "from_code",  self.from_code.strip().upper())
        object.__setattr__(self, "to_code",    self.to_code.strip().upper())
        object.__setattr__(self, "class_code", self.class_code.strip().upper())
        object.__setattr__(self, "quota",      self.quota.strip().upper())

    @property
    def confirmtkt_date_str(self) -> str:
        """Return date in ConfirmTKT's URL format: DD-MM-YYYY."""
        return self.date.strftime("%d-%m-%Y")

    def __str__(self) -> str:
        return (
            f"{self.from_code}→{self.to_code} "
            f"[{self.class_code}/{self.quota}] "
            f"on {self.date.isoformat()}"
        )


# ──────────────────────────────────────────────────────────────
# Output
# ──────────────────────────────────────────────────────────────

VALID_STATUSES = frozenset({"AVAILABLE", "WL", "REGRET", "RAC"})


@dataclass(slots=True)
class AvailabilityResult:
    """Scraped availability for a single train on a single date."""

    train_number:    str
    train_name:      str
    from_code:       str
    to_code:         str
    journey_date:    date
    class_code:      str
    quota:           str
    status:          str           # AVAILABLE | WL | REGRET | RAC
    available_seats: int = 0
    wl_number:       int = 0       # > 0 only when status == "WL"
    fare:            float | None = None
    departure:       str = "00:00" # HH:MM
    arrival:         str = "00:00" # HH:MM
    duration_min:    int = 0
    fetched_at:      datetime = field(default_factory=datetime.utcnow)
    raw_text:        str = ""      # original string from ConfirmTKT for debugging

    def __post_init__(self) -> None:
        self.train_number = self.train_number.strip()
        self.train_name   = self.train_name.strip()
        self.from_code    = self.from_code.strip().upper()
        self.to_code      = self.to_code.strip().upper()
        self.class_code   = self.class_code.strip().upper()
        self.quota        = self.quota.strip().upper()
        # Normalise status
        s = self.status.strip().upper()
        if s not in VALID_STATUSES:
            s = "REGRET"   # safest fallback for unknown states
        self.status = s

    @property
    def is_bookable(self) -> bool:
        return self.status == "AVAILABLE" and self.available_seats > 0

    def __str__(self) -> str:
        seats_info = (
            f"{self.available_seats} seats"
            if self.status == "AVAILABLE"
            else f"WL#{self.wl_number}"
            if self.status == "WL"
            else self.status
        )
        return (
            f"[{self.train_number}] {self.train_name} "
            f"{self.from_code}→{self.to_code} "
            f"[{self.class_code}/{self.quota}] "
            f"{self.journey_date.isoformat()} → {seats_info}"
        )


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def parse_availability_text(raw: str) -> tuple[str, int, int]:
    """
    Parse the availability cell text from IRCTC into
    (status, available_seats, wl_number).

    Examples handled:
      "AVAILABLE - 12"   → ("AVAILABLE", 12, 0)
      "WL# 45"           → ("WL", 0, 45)
      "RAC 8"            → ("RAC", 8, 0)
      "REGRET"           → ("REGRET", 0, 0)
      "REGRET/WL"        → ("REGRET", 0, 0)   # full REGRET takes priority
      "AVAILABLE"        → ("AVAILABLE", 0, 0)  # unknown seat count
    """
    import re

    text = raw.strip().upper()

    # Check REGRET first so "REGRET/WL" is not mis-classified as WL
    if text.startswith("REGRET"):
        return ("REGRET", 0, 0)

    if text.startswith("AVAILABLE"):
        m = re.search(r"(\d+)", text)
        seats = int(m.group(1)) if m else 0
        return ("AVAILABLE", seats, 0)

    if "WL" in text:
        m = re.search(r"(\d+)", text)
        wl = int(m.group(1)) if m else 0
        return ("WL", 0, wl)

    if text.startswith("RAC"):
        m = re.search(r"(\d+)", text)
        seats = int(m.group(1)) if m else 0
        return ("RAC", seats, 0)

    return ("REGRET", 0, 0)

