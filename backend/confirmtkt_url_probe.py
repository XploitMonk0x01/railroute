"""
Probe ConfirmTkt to discover:
1. The search result URL pattern
2. The result-page DOM selectors for train rows
"""
import asyncio
from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await ctx.new_page()

        # ── Step 1: load homepage and wait for app shell ──────
        print("Loading ConfirmTkt homepage …")
        await page.goto("https://www.confirmtkt.com/", wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(8)

        # ── Step 2: click SEARCH with existing pre-filled vals ─
        # The form is pre-filled with NDLS→MMCT; just hit SEARCH
        # to learn the result URL shape.
        search_btn = page.locator("button").filter(has_text="SEARCH")
        btn_count = await search_btn.count()
        print(f"SEARCH buttons found: {btn_count}")
        if btn_count:
            await search_btn.first.click()
        else:
            # fallback: press Enter on the date input
            await page.locator("#dateOfJourney").press("Enter")

        # ── Step 3: wait for navigation ───────────────────────
        await asyncio.sleep(6)
        result_url = page.url
        title = await page.title()
        print(f"Result URL : {result_url}")
        print(f"Page title : {title}")

        # Screenshot
        await page.screenshot(path="/mnt/sda3/Users/smwlc/proj/AI-ML/railroute/confirmtkt_results.png")
        print("Screenshot saved.")

        # ── Step 4: inspect the result DOM ────────────────────
        # Dump outer HTML of elements likely to be train rows
        candidate_selectors = [
            ".train-item",
            ".train-row",
            ".train-card",
            "[class*='train']",
            "[class*='Train']",
            ".result-item",
            "article",
            ".card",
        ]
        for sel in candidate_selectors:
            els = page.locator(sel)
            n = await els.count()
            if n > 0:
                first_text = await els.first.inner_text()
                print(f"\nSelector {sel!r}: {n} elements")
                print(f"  First element text:\n    {first_text[:300]!r}")

        # Dump a chunk of the page HTML to file for analysis
        html = await page.content()
        with open(
            "/mnt/sda3/Users/smwlc/proj/AI-ML/railroute/confirmtkt_results.html", "w"
        ) as f:
            f.write(html)
        print(f"\nFull HTML saved ({len(html):,} bytes)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
