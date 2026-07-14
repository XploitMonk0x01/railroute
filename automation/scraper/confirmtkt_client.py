"""
automation/scraper/confirmtkt_client.py
────────────────────────────────────────
Playwright async scraper for ConfirmTkt seat availability.

URL pattern:
    https://www.confirmtkt.com/rbooking/trains/from/{FROM}/to/{TO}/{DD-MM-YYYY}

Each train card on the results page contains availability sub-cards
for each class/quota combination.

Key DOM structure (as of July 2026):
  Train row:   wraps around a set of class cards
  Class card:  div[data-key="<CLASS>"]._cache-card-wrapper_*
    class code: first <span> in the card header
    fare:       span containing "₹"
    status:     div._prediction-text_*  (text: "Available (N)", "Not Available",
                "WL/12", "REGRET", etc.)
  Train number/name are in the header row above the class cards.
"""

from __future__ import annotations

import asyncio
import logging
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

BASE_URL = "https://www.confirmtkt.com/rbooking/trains/from/{from_code}/to/{to_code}/{date_str}"

MAX_RETRIES        = 3
RETRY_BASE_DELAY_S = 2.0
PAGE_TIMEOUT_MS    = 60_000
NAV_TIMEOUT_MS     = 60_000

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Regex for train numbers (5 digits)
_TRAIN_NUM_RE = re.compile(r"\b(\d{5})\b")
# Regex for fare amounts (₹1,670 or ₹655)
_FARE_RE = re.compile(r"₹\s*([\d,]+)")
# Regex for available seats count from status like "Available (42)"
_AVAIL_SEATS_RE = re.compile(r"Available\s*\((\d+)\)", re.IGNORECASE)
# Regex for WL number like "WL/12" or "WL12"
_WL_RE = re.compile(r"WL[/\s]*(\d+)", re.IGNORECASE)


# ──────────────────────────────────────────────────────────────
# Main client
# ──────────────────────────────────────────────────────────────

class ConfirmTktClient:
    """
    Async context-manager that owns one Playwright Browser + BrowserContext.
    No login required — ConfirmTkt shows cached availability publicly.
    """

    def __init__(
        self,
        headless:   bool = True,
        max_tabs:   int  = 4,
        timeout_ms: int  = PAGE_TIMEOUT_MS,
    ) -> None:
        self._headless   = headless
        self._max_tabs   = max_tabs
        self._timeout_ms = timeout_ms
        self._playwright: Playwright | None     = None
        self._browser:    Browser | None        = None
        self._context:    BrowserContext | None = None

    # ── lifecycle ────────────────────────────────────────────

    async def __aenter__(self) -> "ConfirmTktClient":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9,hi;q=0.8"},
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

    # ── public API ───────────────────────────────────────────

    async def check_availability(self, query: RouteQuery) -> list[AvailabilityResult]:
        """
        Fetch availability for a single RouteQuery from ConfirmTkt.
        Retries up to MAX_RETRIES times on transient failures.
        """
        assert self._context, "Client not started — use as async context manager."

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._scrape(query)
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                    log.warning(
                        "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                        attempt, MAX_RETRIES, query, exc, delay,
                    )
                    await asyncio.sleep(delay)

        log.error("All %d attempts failed for %s: %s", MAX_RETRIES, query, last_error)
        return []

    async def multi_tab_search(
        self,
        queries: Sequence[RouteQuery],
    ) -> list[AvailabilityResult]:
        """Run multiple queries concurrently (batched by max_tabs)."""
        all_results: list[AvailabilityResult] = []
        queue = list(queries)

        log.info(
            "ConfirmTkt: %d queries, max %d parallel tabs",
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

        log.info("ConfirmTkt: %d results collected.", len(all_results))
        return all_results

    # ── private scraping logic ───────────────────────────────

    async def _scrape(self, query: RouteQuery) -> list[AvailabilityResult]:
        """Open a tab, navigate to the direct URL, parse results, close tab."""
        page = await self._context.new_page()
        if _STEALTH_AVAILABLE:
            await stealth_async(page)

        results: list[AvailabilityResult] = []
        date_str = query.date.strftime("%d-%m-%Y")
        url = BASE_URL.format(
            from_code=query.from_code,
            to_code=query.to_code,
            date_str=date_str,
        )

        try:
            log.debug("Navigating to %s", url)
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)

            # Dismiss any modal/popup (e.g. FCF insurance prompt)
            try:
                dismiss = page.locator("button:has-text('Not now')").first
                if await dismiss.is_visible(timeout=4_000):
                    await dismiss.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            # Wait for train cards to render
            try:
                await page.wait_for_selector(
                    "[data-key], ._cache-card-wrapper_89zaw_12",
                    timeout=25_000,
                )
            except Exception:
                log.warning("No availability cards found for %s", query)
                return []

            await asyncio.sleep(1.5)  # let remaining cards render

            results = await self._parse_results(page, query)
            log.info("ConfirmTkt: %s → %d results", query, len(results))

        finally:
            await page.close()

        return results

    async def _parse_results(
        self, page: Page, query: RouteQuery
    ) -> list[AvailabilityResult]:
        """
        Parse the ConfirmTkt results page.

        DOM structure (confirmed July 2026):
          <div id="train-12903" class="border-b border-tertiary bg-primary ...">
            <div class="body-sm max-w-[215px] ...">
              <span class="mr-5">12903</span>Golden Temple
            </div>
            ...
            <div class="flex gap-[12px]">
              <div data-key="SL" class="_cache-card-wrapper_*">
                1 hr ago ... SL ... ₹540 ... AVL 92 ... Available
              </div>
            </div>
          </div>

        Strategy:
          1. Find all train wrapper divs by id="train-XXXXX"
          2. Extract train number from the id attribute
          3. Extract train name from the .body-sm container text
          4. For each [data-key] card inside, parse class, fare, and status
        """
        results: list[AvailabilityResult] = []

        # Find all train wrapper divs (id="train-NNNNN")
        train_wrappers = page.locator("[id^='train-']")
        wrapper_count = await train_wrappers.count()
        log.debug("Found %d train wrappers on page", wrapper_count)

        if wrapper_count == 0:
            log.warning("No train wrappers found for %s", query)
            return results

        for wi in range(wrapper_count):
            wrapper = train_wrappers.nth(wi)
            try:
                wrapper_id = await wrapper.get_attribute("id") or ""
                # id is like "train-12903"
                id_m = re.match(r"train-(\d{5})", wrapper_id)
                if not id_m:
                    continue
                train_number = id_m.group(1)

                # Extract train name from the name container
                try:
                    name_container = wrapper.locator(".body-sm").first
                    full_name_text = (await name_container.inner_text(timeout=2_000)).strip()
                    train_name = full_name_text.replace(train_number, "").strip()
                except Exception:
                    train_name = "Unknown"

                # Find all class cards within this train wrapper
                class_cards = wrapper.locator("[data-key]")
                card_count = await class_cards.count()

                for ci in range(card_count):
                    card = class_cards.nth(ci)
                    try:
                        class_code = await card.get_attribute("data-key") or ""

                        # Filter by requested class
                        if query.class_code and class_code != query.class_code:
                            continue

                        card_text = (await card.inner_text()).strip()

                        # Extract fare (₹540)
                        fare_match = _FARE_RE.search(card_text)
                        fare: float | None = None
                        if fare_match:
                            try:
                                fare = float(fare_match.group(1).replace(",", ""))
                            except ValueError:
                                pass

                        # Card text format: "1 hr ago\n\nSL\n₹540\nAVL 92\nAvailable"
                        # or "... \nNot Available" / "... \nWL/12\nWaitlist" / "... \nRAC 3\nRAC"
                        lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                        # Last line is the human-readable label; second-to-last has the count
                        last_line = lines[-1].upper() if lines else ""
                        avl_line  = lines[-2].upper() if len(lines) >= 2 else ""
                        combined  = f"{avl_line} {last_line}".strip()  # always defined for raw_text

                        # ── ConfirmTkt-specific status parsing ──────────────
                        avl_m  = re.match(r"AVL\s*(\d+)", avl_line)
                        wl_m   = re.match(r"WL[/\s]*(\d+)", avl_line)
                        rac_m  = re.match(r"RAC\s*(\d+)", avl_line)

                        if "NOT AVAILABLE" in last_line or "REGRET" in last_line:
                            status, seats, wl = "REGRET", 0, 0
                        elif avl_m and "AVAILABLE" in last_line:
                            status, seats, wl = "AVAILABLE", int(avl_m.group(1)), 0
                        elif "AVAILABLE" in last_line:
                            status, seats, wl = "AVAILABLE", 0, 0
                        elif wl_m:
                            wl_num = int(wl_m.group(1))
                            status, seats, wl = "WL", -wl_num, wl_num
                        elif rac_m:
                            status, seats, wl = "RAC", int(rac_m.group(1)), 0
                        else:
                            # Fallback to shared parser with the last two lines combined
                            status, seats, wl = parse_availability_text(combined)


                        results.append(
                            AvailabilityResult(
                                train_number=train_number,
                                train_name=train_name,
                                from_code=query.from_code,
                                to_code=query.to_code,
                                journey_date=query.date,
                                class_code=class_code or query.class_code,
                                quota=query.quota,
                                status=status,
                                available_seats=seats,
                                wl_number=wl,
                                fare=fare,
                                fetched_at=datetime.utcnow(),
                                raw_text=combined,
                            )
                        )

                    except Exception as card_exc:
                        log.debug("Skipping card %d of train %s: %s", ci, train_number, card_exc)

            except Exception as wrapper_exc:
                log.debug("Skipping train wrapper %d: %s", wi, wrapper_exc)

        # Deduplicate by (train_number, class_code) keeping highest seats
        seen: dict[tuple[str, str], AvailabilityResult] = {}
        for r in results:
            key = (r.train_number, r.class_code)
            if key not in seen or r.available_seats > seen[key].available_seats:
                seen[key] = r

        return list(seen.values())
