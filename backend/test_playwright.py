"""
Playwright smoke test — run with:
    .venv/bin/python test_playwright.py
"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    print("Starting Playwright …")
    async with async_playwright() as p:
        print("Launching Chromium (headless) …")
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()

        # ── Step 1: basic navigation ──────────────────────────
        print("Navigating to example.com …")
        await page.goto("https://example.com", wait_until="domcontentloaded")
        title = await page.title()
        print(f"  ✓ Page title: {title!r}")

        # ── Step 2: attempt IRCTC train-search (no login) ─────
        print("Navigating to IRCTC train-search …")
        try:
            await page.goto(
                "https://www.irctc.co.in/nget/train-search",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            irctc_title = await page.title()
            print(f"  ✓ IRCTC page title: {irctc_title!r}")

            # Check whether the From-station input is visible
            from_inp = page.locator(
                "input[placeholder*='From Station'],"
                "input[formcontrolname*='from']"
            ).first
            visible = await from_inp.is_visible()
            print(f"  ✓ From-station input visible: {visible}")
        except Exception as e:
            print(f"  ✗ IRCTC navigation failed: {e}")

        await browser.close()
        print("\nSmoke test complete.")


if __name__ == "__main__":
    asyncio.run(main())
