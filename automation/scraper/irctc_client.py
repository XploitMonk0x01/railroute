"""
automation/scraper/irctc_client.py
────────────────────────────────────
Pure Playwright async scraper for IRCTC seat availability.

Key design choices
──────────────────
• playwright-stealth: spoofs browser fingerprint (navigator.webdriver, plugins,
  user-agent, etc.) so Cloudflare bot detection doesn't trigger.
• One BrowserContext per IRCTCClient: all tabs share cookies, so login is done
  once and all parallel queries reuse the authenticated session.
• asyncio.gather() drives the multi-tab search — each query gets its own Page
  object opened inside the shared context.
• Retry/back-off: each individual search tab retries up to MAX_RETRIES times
  with exponential back-off before giving up and returning an empty list.

Usage
─────
    async with IRCTCClient(headless=False) as client:
        await client.login("user", "pass")
        results = await client.multi_tab_search([
            RouteQuery("HWH", "PNBE", date(2026,7,20), "3A"),
            RouteQuery("HWH", "ASN",  date(2026,7,20), "3A"),
        ])
        for r in results:
            print(r)
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
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

IRCTC_BASE   = "https://www.irctc.co.in"
IRCTC_LOGIN  = f"{IRCTC_BASE}/nget/train-search"
IRCTC_SEARCH = f"{IRCTC_BASE}/nget/train-search"

MAX_RETRIES        = 3
RETRY_BASE_DELAY_S = 2.0    # seconds; doubled on each retry
PAGE_TIMEOUT_MS    = 60_000  # 60 s per page operation
NAV_TIMEOUT_MS     = 90_000  # 90 s navigation

# Realistic user-agent string (Chrome 124 on Linux)
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _jitter(base: float) -> float:
    """Add ±20 % random jitter to a delay to reduce detection."""
    return base * (0.8 + random.random() * 0.4)


async def _maybe_stealth(page: Page) -> None:
    if _STEALTH_AVAILABLE:
        await stealth_async(page)
    else:
        log.warning(
            "playwright-stealth not installed; "
            "bot detection may trigger. "
            "Install it with: pip install playwright-stealth"
        )


# ──────────────────────────────────────────────────────────────
# Main client
# ──────────────────────────────────────────────────────────────

class IRCTCClient:
    """
    Async context-manager that owns one Playwright Browser + BrowserContext.
    All scraping operations are performed inside that context (shared cookies).
    """

    def __init__(
        self,
        headless:  bool = False,
        max_tabs:  int  = 6,
        timeout_ms: int = PAGE_TIMEOUT_MS,
    ) -> None:
        self._headless   = headless
        self._max_tabs   = max_tabs
        self._timeout_ms = timeout_ms
        self._playwright: Playwright | None     = None
        self._browser:    Browser | None        = None
        self._context:    BrowserContext | None = None
        self._logged_in:  bool                  = False

    # ── lifecycle ────────────────────────────────────────────

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
            viewport={"width": 1366, "height": 768},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            # Mimic a real Indian browser session
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
        self._logged_in = False

    # ── authentication ───────────────────────────────────────

    async def login(self, username: str, password: str) -> None:
        """
        Log into IRCTC.  Opens a dedicated login page, fills credentials,
        handles the CAPTCHA prompt (pauses for manual entry when not headless),
        and waits for the dashboard to confirm success.
        """
        assert self._context, "Client not started — use as async context manager."
        page = await self._context.new_page()
        await _maybe_stealth(page)

        log.info("Navigating to IRCTC login page …")
        await page.goto(IRCTC_LOGIN, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        await asyncio.sleep(_jitter(2))

        # ── dismiss cookie banner if present ────────────────
        try:
            cookie_btn = page.locator("button:has-text('Accept')")
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            pass  # no cookie banner — continue

        # ── click the Login button in the top nav ──────────
        try:
            login_nav = page.locator("a.search_btn_new:has-text('LOGIN')")
            if await login_nav.is_visible(timeout=5000):
                await login_nav.click()
                await asyncio.sleep(_jitter(1.5))
        except Exception:
            log.debug("Login nav button not found; may already be on login form.")

        # ── fill username ────────────────────────────────────
        user_input = page.locator("input#userId, input[placeholder*='User Name']").first
        await user_input.wait_for(state="visible", timeout=10_000)
        await user_input.click()
        await asyncio.sleep(_jitter(0.3))
        await user_input.type(username, delay=_jitter(80))

        # ── fill password ────────────────────────────────────
        pass_input = page.locator("input#pwd, input[type='password']").first
        await pass_input.click()
        await asyncio.sleep(_jitter(0.3))
        await pass_input.type(password, delay=_jitter(80))

        if not self._headless:
            # IRCTC has image CAPTCHA — pause and let the user solve it manually.
            log.warning(
                "\n"
                "┌──────────────────────────────────────────────────────────┐\n"
                "│  IRCTC CAPTCHA detected.                                 │\n"
                "│  Please solve the CAPTCHA in the browser window,        │\n"
                "│  then click SIGN IN manually.                            │\n"
                "│  The script will continue automatically once you are     │\n"
                "│  redirected to the home / dashboard page.                │\n"
                "└──────────────────────────────────────────────────────────┘"
            )
            # Wait up to 5 minutes for a successful redirect
            await page.wait_for_url(
                lambda url: "login" not in url.lower() and "irctc" in url.lower(),
                timeout=300_000,
            )
        else:
            # Headless mode — attempt automatic sign-in (CAPTCHA may fail)
            sign_in_btn = page.locator("button#loginBtn, button:has-text('SIGN IN')")
            await sign_in_btn.click()
            await page.wait_for_load_state("networkidle", timeout=30_000)

        self._logged_in = True
        log.info("IRCTC login successful.")
        await page.close()

    # ── single-query search ──────────────────────────────────

    async def check_availability(self, query: RouteQuery) -> list[AvailabilityResult]:
        """
        Search for trains on a single RouteQuery.
        Returns a list of AvailabilityResult — one per matching train found.
        Retries up to MAX_RETRIES times on transient failures.
        """
        assert self._context, "Client not started."

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
        """
        Run multiple RouteQuery searches concurrently, each in its own browser tab.
        Tabs are batched so at most `max_tabs` run at the same time.
        Results from all tabs are concatenated and returned.
        """
        all_results: list[AvailabilityResult] = []
        queue = list(queries)

        log.info(
            "Starting multi-tab search: %d queries, max %d parallel tabs",
            len(queue), self._max_tabs,
        )

        while queue:
            batch = queue[: self._max_tabs]
            queue = queue[self._max_tabs :]

            log.info("  Batch: %d queries …", len(batch))
            batch_results = await asyncio.gather(
                *[self.check_availability(q) for q in batch],
                return_exceptions=False,
            )
            for r in batch_results:
                all_results.extend(r)

        log.info("Multi-tab search complete. %d results collected.", len(all_results))
        return all_results

    # ── private page-level search ────────────────────────────

    async def _search_on_new_page(self, query: RouteQuery) -> list[AvailabilityResult]:
        """Open a new tab, perform the search, parse the table, close the tab."""
        page = await self._context.new_page()
        await _maybe_stealth(page)
        results: list[AvailabilityResult] = []

        try:
            log.debug("Tab opened for %s", query)
            await page.goto(IRCTC_SEARCH, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            await asyncio.sleep(_jitter(1.5))

            # ── fill From station ──────────────────────────
            await self._fill_station(page, "from", query.from_code)
            await asyncio.sleep(_jitter(0.8))

            # ── fill To station ────────────────────────────
            await self._fill_station(page, "to", query.to_code)
            await asyncio.sleep(_jitter(0.8))

            # ── fill journey date ──────────────────────────
            await self._fill_date(page, query.date)
            await asyncio.sleep(_jitter(0.6))

            # ── click Search button ────────────────────────
            search_btn = page.locator(
                "button.search_btn, button:has-text('Search'), "
                "button[type='submit']"
            ).first
            await search_btn.click()
            await asyncio.sleep(_jitter(2))

            # ── wait for results table ─────────────────────
            try:
                await page.wait_for_selector(
                    "app-train-avl-enq, .trainTable, table.table-condensed",
                    timeout=30_000,
                )
            except Exception:
                log.warning("No results table appeared for %s", query)
                return []

            # ── filter by class / quota ────────────────────
            await self._select_class_quota(page, query.class_code, query.quota)
            await asyncio.sleep(_jitter(1))

            # ── parse results ──────────────────────────────
            results = await self._parse_results(page, query)
            log.info("  %s → %d trains found", query, len(results))

        finally:
            await page.close()

        return results

    # ── form interaction helpers ─────────────────────────────

    async def _fill_station(self, page: Page, field: str, code: str) -> None:
        """Type a station code into the from/to autocomplete and select it."""
        # IRCTC uses Angular Material autocomplete inputs
        selector = (
            f"input[placeholder*='{field.title()} Station'],"
            f"input[id*='{field}'],"
            f"input[formcontrolname='{field}Station']"
        )
        inp = page.locator(selector).first
        await inp.wait_for(state="visible", timeout=10_000)
        await inp.triple_click()
        await inp.type(code, delay=_jitter(100))
        await asyncio.sleep(_jitter(1.2))

        # Wait for dropdown suggestion and click exact match
        option = page.locator(
            f"span:has-text('{code}'), "
            f"li:has-text('{code}'), "
            f"mat-option:has-text('{code}')"
        ).first
        try:
            await option.click(timeout=6_000)
        except Exception:
            # Fallback: press Enter to accept first suggestion
            await inp.press("Enter")

    async def _fill_date(self, page: Page, journey_date: date) -> None:
        """Fill the journey date field (handles both input[type=date] and datepicker)."""
        date_str_iso  = journey_date.strftime("%Y-%m-%d")
        date_str_dmy  = journey_date.strftime("%d/%m/%Y")  # IRCTC display format

        date_inp = page.locator(
            "input[type='date'],"
            "input[placeholder*='Date'],"
            "input[formcontrolname*='date'],"
            "input[formcontrolname*='Date']"
        ).first

        try:
            await date_inp.wait_for(state="visible", timeout=5_000)
            await date_inp.triple_click()
            await date_inp.fill(date_str_iso)
            # Fallback type if fill doesn't trigger Angular change detection
            if not await date_inp.input_value():
                await date_inp.type(date_str_dmy, delay=_jitter(60))
        except Exception:
            log.warning("Could not fill date field — trying datepicker workaround.")
            # Click the calendar icon and navigate to the right month
            try:
                cal_btn = page.locator("span.p-datepicker-trigger, mat-datepicker-toggle").first
                await cal_btn.click(timeout=5_000)
                await asyncio.sleep(0.5)
                # Type in the input that appears in the picker
                picker_inp = page.locator("input.p-inputtext").first
                await picker_inp.fill(date_str_dmy)
                await picker_inp.press("Enter")
            except Exception as e:
                log.error("Date fill failed completely: %s", e)

    async def _select_class_quota(
        self, page: Page, class_code: str, quota: str
    ) -> None:
        """Select the travel class and quota in the results filter row."""
        # Class dropdown / tab
        try:
            class_sel = page.locator(
                f"button:has-text('{class_code}'),"
                f"td:has-text('{class_code}'),"
                f"span:has-text('{class_code}')"
            ).first
            if await class_sel.is_visible(timeout=4_000):
                await class_sel.click()
                await asyncio.sleep(_jitter(0.6))
        except Exception:
            log.debug("Class selector not found — using default class.")

        # Quota dropdown
        try:
            quota_sel = page.locator(
                "select[formcontrolname*='quota'],"
                "select[id*='quota']"
            ).first
            if await quota_sel.is_visible(timeout=4_000):
                await quota_sel.select_option(value=quota)
                await asyncio.sleep(_jitter(0.6))
        except Exception:
            log.debug("Quota selector not found — using default quota.")

    # ── result parsing ───────────────────────────────────────

    async def _parse_results(
        self, page: Page, query: RouteQuery
    ) -> list[AvailabilityResult]:
        """
        Extract train availability rows from whatever table IRCTC renders.
        IRCTC's Angular SPA renders rows inside:
          • <app-train-avl-enq> components  (new site)
          • <table class="table-condensed"> (legacy fallback)
        We handle both by extracting text from each row.
        """
        results: list[AvailabilityResult] = []

        try:
            # ── strategy 1: Angular component rows ────────
            rows = page.locator(
                "app-train-avl-enq .table-responsive tr, "
                ".trainTable tr, "
                "table.table-condensed tr"
            )
            count = await rows.count()

            for i in range(count):
                row = rows.nth(i)
                cells = row.locator("td")
                cell_count = await cells.count()
                if cell_count < 3:
                    continue  # header or spacer row

                try:
                    # IRCTC column layout (varies but typically):
                    # 0: Train No + Name  1: From-To time  2: Class avail  3: Fare …
                    raw_train = (await cells.nth(0).inner_text()).strip()
                    raw_avail = (await cells.nth(cell_count - 1).inner_text()).strip()

                    # Extract train number (first word / 5-digit code)
                    import re
                    m_num = re.search(r"\b(\d{5})\b", raw_train)
                    if not m_num:
                        continue
                    train_number = m_num.group(1)
                    train_name   = raw_train.replace(train_number, "").strip(" -|")

                    # Parse availability cell
                    status, seats, wl = parse_availability_text(raw_avail)

                    # Try to extract fare
                    fare: float | None = None
                    m_fare = re.search(r"₹\s*([\d,]+)|Rs\.?\s*([\d,]+)", raw_avail)
                    if m_fare:
                        fare_str = (m_fare.group(1) or m_fare.group(2)).replace(",", "")
                        try:
                            fare = float(fare_str)
                        except ValueError:
                            pass

                    results.append(
                        AvailabilityResult(
                            train_number    = train_number,
                            train_name      = train_name or "Unknown",
                            from_code       = query.from_code,
                            to_code         = query.to_code,
                            journey_date    = query.date,
                            class_code      = query.class_code,
                            quota           = query.quota,
                            status          = status,
                            available_seats = seats,
                            wl_number       = wl,
                            fare            = fare,
                            fetched_at      = datetime.utcnow(),
                            raw_text        = raw_avail,
                        )
                    )
                except Exception as cell_exc:
                    log.debug("Skipping row %d: %s", i, cell_exc)

        except Exception as exc:
            log.error("Result parsing failed: %s", exc)

        return results
