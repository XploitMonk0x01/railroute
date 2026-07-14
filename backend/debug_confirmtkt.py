"""
Debug script: loads the ConfirmTkt results page for BRC→NDLS,
takes a screenshot, and dumps the DOM to figure out why parsing fails.
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "automation"))

from playwright.async_api import async_playwright


async def main() -> None:
    url = "https://www.confirmtkt.com/rbooking/trains/from/BRC/to/NDLS/31-07-2026"

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

        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # Dismiss popup if present
        try:
            btn = page.locator("button:has-text('Not now')").first
            if await btn.is_visible(timeout=5_000):
                await btn.click()
                print("Dismissed popup")
        except Exception:
            pass

        # Try to wait for train cards
        print("Waiting for [data-key] cards...")
        try:
            await page.wait_for_selector("[data-key]", timeout=25_000)
            print("  ✓ [data-key] cards found")
        except Exception as e:
            print(f"  ✗ [data-key] not found: {e}")

        await asyncio.sleep(2)

        # Screenshot
        await page.screenshot(
            path="/mnt/sda3/Users/smwlc/proj/AI-ML/railroute/ctkt_brc_ndls.png",
            full_page=False,
        )
        print("Screenshot saved.")

        # Count cards
        cards = page.locator("[data-key]")
        cnt = await cards.count()
        print(f"\n[data-key] card count: {cnt}")

        # Show first few cards text
        for i in range(min(cnt, 5)):
            card = cards.nth(i)
            key = await card.get_attribute("data-key")
            text = (await card.inner_text()).strip()
            print(f"  Card {i}: data-key={key!r}  text={text[:120]!r}")

        # Now try the JS DOM walk on card 0
        if cnt > 0:
            card0 = await cards.first.element_handle()
            train_info = await page.evaluate(
                """(cardEl) => {
                    let el = cardEl;
                    for (let i = 0; i < 10; i++) {
                        el = el.parentElement;
                        if (!el) break;
                        const txt = el.innerText || '';
                        const m = txt.match(/\\b(\\d{5})\\b/);
                        if (m) {
                            return { number: m[1], parentClass: el.className, textSnip: txt.substring(0, 200) };
                        }
                    }
                    return { number: 'NOT FOUND', textSnip: '' };
                }""",
                card0,
            )
            print(f"\nTrain info from DOM walk: {train_info}")

        # Also dump page title + URL
        print(f"\nFinal URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Dump full HTML
        html = await page.content()
        with open("/mnt/sda3/Users/smwlc/proj/AI-ML/railroute/ctkt_brc_ndls.html", "w") as f:
            f.write(html)
        print(f"HTML saved ({len(html):,} bytes)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
