"""
automation/scraper/irctc_client.py
────────────────────────────────────
Playwright async scraper for ConfirmTKT seat availability.
No login required — ConfirmTKT is a public aggregator.

URL format:
  https://www.confirmtkt.com/rbooking/trains/from/{FROM}/to/{TO}/{DD-MM-YYYY}

DOM structure (as of July 2026):
  - Train cards: div[id^='train-'] (e.g. id="train-12506")
  - Train number + name: div.body-sm > span.mr-5 (number) + text (name)
  - Departure: first div.body-sm.text-left.font-medium ("07:35 DLI")
  - Arrival:  second div.body-sm.text-left.font-medium ("21:45 PPTA")
  - Duration: p.body-xs.inline-block.text-secondary ("14h 5m")
  - Availability per class: div[data-key="3A"] etc.
    - Status: div[class*='_prediction-text'] or p.body-sm.truncate ("AVL 93" / "WL 10")
    - Fare: span containing "₹"
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import date, datetime
from typing import Sequence

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

try:
    from playwright_stealth import stealth_async  # type: ignore
    _STEALTH_AVAILABLE = True
except ImportError:
    _STEALTH_AVAILABLE = False

from .models import AvailabilityResult, RouteQuery, parse_availability_text

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

CONFIRMTKT_BASE = "https://www.confirmtkt.com/rbooking/trains/from/{from_code}/to/{to_code}/{date_str}"

MAX_RETRIES        = 3
RETRY_BASE_DELAY_S = 2.0
PAGE_TIMEOUT_MS    = 60_000
NAV_TIMEOUT_MS     = 90_000

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _jitter(base: float) -> float:
    return base * (0.8 + random.random() * 0.4)


async def _maybe_stealth(page: Page) -> None:
    if _STEALTH_AVAILABLE:
        await stealth_async(page)


def _build_confirmtkt_url(query: RouteQuery) -> str:
    date_str = query.date.strftime("%d-%m-%Y")
    return CONFIRMTKT_BASE.format(
        from_code=query.from_code.upper(),
        to_code=query.to_code.upper(),
        date_str=date_str,
    )


# ──────────────────────────────────────────────────────────────
# Main client
# ──────────────────────────────────────────────────────────────

class IRCTCClient:
    """
    Async context-manager that scrapes ConfirmTKT (no login required).
    Class name kept as IRCTCClient for backward compatibility.
    """

    def __init__(
        self,
        headless:   bool = False,
        max_tabs:   int  = 6,
        timeout_ms: int  = PAGE_TIMEOUT_MS,
    ) -> None:
        self._headless   = headless
        self._max_tabs   = max_tabs
        self._timeout_ms = timeout_ms
        self._playwright: Playwright | None     = None
        self._browser:    Browser | None        = None
        self._context:    BrowserContext | None = None

    async def __aenter__(self) -> "IRCTCClient":
        self._playwright = await async_playwright().start()
        self._browser    = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            },
        )
        self._context.set_default_timeout(self._timeout_ms)
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def login(self, username: str, password: str) -> None:
        """No-op — ConfirmTKT does not require login."""
        pass

    # ── single-query search ──────────────────────────────────

    async def check_availability(self, query: RouteQuery) -> list[AvailabilityResult]:
        assert self._context, "Client not started — use as async context manager."
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._search_on_new_page(query)
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = _jitter(RETRY_BASE_DELAY_S * (2 ** (attempt - 1)))
                    log.warning(
                        "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                        attempt, MAX_RETRIES, query, exc, delay,
                    )
                    await asyncio.sleep(delay)
        log.error("All %d attempts failed for %s: %s", MAX_RETRIES, query, last_error)
        return []

    # ── multi-tab parallel search ────────────────────────────

    async def multi_tab_search(
        self,
        queries: Sequence[RouteQuery],
    ) -> list[AvailabilityResult]:
        all_results: list[AvailabilityResult] = []
        queue = list(queries)
        log.info(
            "Starting ConfirmTKT search: %d queries, max %d parallel tabs",
            len(queue), self._max_tabs,
        )
        while queue:
            batch = queue[: self._max_tabs]
            queue = queue[self._max_tabs :]
            batch_results = await asyncio.gather(
                *[self.check_availability(q) for q in batch],
                return_exceptions=False,
            )
            for r in batch_results:
                all_results.extend(r)
        log.info("Search complete. %d results collected.", len(all_results))
        return all_results

    # ── private page-level search ────────────────────────────

    async def _search_on_new_page(self, query: RouteQuery) -> list[AvailabilityResult]:
        page = await self._context.new_page()
        await _maybe_stealth(page)
        
        # Block unnecessary resources for faster scraping and less detection surface
        async def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            elif any(x in route.request.url for x in ["google-analytics", "facebook.com", "doubleclick", "ads"]):
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_resources)
        
        # Safe background task to auto-dismiss popups while page is active
        async def popup_monitor():
            while not page.is_closed():
                try:
                    for sel in ["text=Not now", "button:has-text('Not now')"]:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=500):
                            await btn.click(timeout=1000)
                            log.info("Dismissed FCF popup automatically.")
                            await asyncio.sleep(2)  # pause after clicking
                except Exception:
                    pass
                await asyncio.sleep(1)

        monitor_task = asyncio.create_task(popup_monitor())

        results: list[AvailabilityResult] = []

        try:
            url = _build_confirmtkt_url(query)
            log.info("Navigating to: %s", url)
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            await asyncio.sleep(_jitter(3))

            # Wait for train cards to appear (id="train-XXXXX")
            try:
                await page.wait_for_selector(
                    "div[id^='train-']",
                    timeout=20_000,
                )
                log.info("Train cards loaded for %s", query)
            except Exception:
                await asyncio.sleep(3)
                # Check if any train cards appeared after extra wait
                count = await page.locator("div[id^='train-']").count()
                if count == 0:
                    log.warning("No train cards found for %s", query)
                    return []

            # Wait for availability data to populate via background API calls
            try:
                await page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass  # Ignore timeout, some ads/analytics might still be loading

            # Parse the train cards
            results = await self._parse_train_cards(page, query)
            log.info("  %s → %d results parsed", query, len(results))

        finally:
            monitor_task.cancel()
            await page.close()

        return results



    # ── result parsing using exact ConfirmTKT DOM selectors ──

    async def _parse_train_cards(
        self, page: Page, query: RouteQuery
    ) -> list[AvailabilityResult]:
        """
        Parse train cards from ConfirmTKT's DOM.
        
        Each train card has:
          div[id="train-XXXXX"]
            div.body-sm > span.mr-5 (train number) + text (train name)
            Availability cards: div[data-key="3A"], div[data-key="SL"] etc.
              Status: text like "AVL 93", "WL 10", "RAC 63"
              Fare: span with "₹" prefix
        """
        results: list[AvailabilityResult] = []
        train_cards = page.locator("div[id^='train-']")
        card_count = await train_cards.count()
        log.debug("Found %d train cards", card_count)

        for i in range(card_count):
            card = train_cards.nth(i)
            try:
                # Extract train number from the id attribute (e.g. "train-12506")
                card_id = await card.get_attribute("id")
                if not card_id:
                    continue
                train_number = card_id.replace("train-", "")
                if not re.match(r"^\d{4,5}$", train_number):
                    continue

                # Extract train name from the text next to span.mr-5
                try:
                    name_div = card.locator("div.body-sm.max-w-\\[215px\\]").first
                    full_text = (await name_div.inner_text()).strip()
                    # full_text is like "12506North East Exp" or "12506 North East Exp"
                    train_name = re.sub(r"^\d{4,5}\s*", "", full_text).strip()
                    if not train_name:
                        train_name = "Unknown"
                except Exception:
                    train_name = "Unknown"

                # Extract departure, arrival, duration
                departure = "00:00"
                arrival = "00:00"
                duration_min = 0
                try:
                    # departure looks like "07:35 DLI" or just "07:35"
                    dep_divs = card.locator("div.body-sm.text-left.font-medium")
                    if await dep_divs.count() >= 2:
                        dep_text = await dep_divs.nth(0).inner_text()
                        arr_text = await dep_divs.nth(1).inner_text()
                        
                        dm = re.search(r"(\d{2}:\d{2})", dep_text)
                        if dm: departure = dm.group(1)
                        
                        am = re.search(r"(\d{2}:\d{2})", arr_text)
                        if am: arrival = am.group(1)
                        
                    # duration looks like "14h 5m" or "16h 53m"
                    dur_p = card.locator("p.body-xs.inline-block.text-secondary").first
                    if await dur_p.count() > 0:
                        dur_text = await dur_p.inner_text()
                        h_match = re.search(r"(\d+)h", dur_text)
                        m_match = re.search(r"(\d+)m", dur_text)
                        h = int(h_match.group(1)) if h_match else 0
                        m = int(m_match.group(1)) if m_match else 0
                        duration_min = h * 60 + m
                except Exception as e:
                    log.debug("Error parsing time/duration for %s: %s", train_number, e)

                # Find the availability card matching the requested class
                class_code = query.class_code.upper()
                avail_card = card.locator(f"div[data-key='{class_code}']")
                
                if await avail_card.count() == 0:
                    # Requested class not available for this train — skip
                    continue

                avail_card = avail_card.first
                avail_text = (await avail_card.inner_text()).strip()

                # Parse status from the availability text
                # Text looks like: "36 mins ago\n3A\n₹1380\nWL 4\nConfirm or 3X Refund*\nWaitlist"
                # or: "36 mins ago\n3A\n₹1340\nAVL 1\nAvailable"
                status, seats, wl = self._parse_avail_text(avail_text)

                # Extract fare
                fare = self._extract_fare(avail_text)

                results.append(
                    AvailabilityResult(
                        train_number    = train_number,
                        train_name      = train_name,
                        from_code       = query.from_code,
                        to_code         = query.to_code,
                        journey_date    = query.date,
                        class_code      = class_code,
                        quota           = query.quota,
                        status          = status,
                        available_seats = seats,
                        wl_number       = wl,
                        fare            = fare,
                        departure       = departure,
                        arrival         = arrival,
                        duration_min    = duration_min,
                        fetched_at      = datetime.utcnow(),
                        raw_text        = avail_text[:200],
                    )
                )

            except Exception as e:
                log.debug("Error parsing train card %d: %s", i, e)

        return results

    def _parse_avail_text(self, text: str) -> tuple[str, int, int]:
        """
        Parse availability from the card text.
        Examples:
          "...AVL 93..."  → ("AVAILABLE", 93, 0)
          "...WL 10..."   → ("WL", 0, 10)
          "...RAC 63..."  → ("RAC", 63, 0)
          "...REGRET..."  → ("REGRET", 0, 0)
        """
        upper = text.upper()

        # Check AVL (Available) first
        m = re.search(r"AVL\s+(\d+)", upper)
        if m:
            return ("AVAILABLE", int(m.group(1)), 0)

        # Check RAC
        m = re.search(r"RAC\s+(\d+)", upper)
        if m:
            return ("RAC", int(m.group(1)), 0)

        # Check WL (Waitlist)
        m = re.search(r"WL\s+(\d+)", upper)
        if m:
            return ("WL", 0, int(m.group(1)))

        # Check REGRET
        if "REGRET" in upper:
            return ("REGRET", 0, 0)

        # Fallback: if "Available" appears but no number
        if "AVAILABLE" in upper:
            return ("AVAILABLE", 0, 0)

        return ("REGRET", 0, 0)

    def _extract_fare(self, text: str) -> float | None:
        """Extract fare from text containing ₹ symbol."""
        m = re.search(r"₹\s*([\d,]+)", text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
        return None
