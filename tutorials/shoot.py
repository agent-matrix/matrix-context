#!/usr/bin/env python3
"""Capture screenshots of the Matrix Context Console for the tutorial.

Transient tooling (Playwright is not a project dependency). Start the app first:

    python frontend/server.py            # http://127.0.0.1:7860
    python -m pip install playwright && python -m playwright install chromium
    python tutorials/shoot.py             # -> tutorials/screenshots/*.png
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:7860"
OUT = Path(__file__).parent / "screenshots"


async def settle(page, ms=900):
    await page.wait_for_timeout(ms)


async def shot(page, name):
    await settle(page)
    OUT.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print("shot:", name)


async def tab(page, key):
    await page.click(f'.tab[data-tab="{key}"]')
    await settle(page, 700)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900},
                                        device_scale_factor=2, color_scheme="dark")
        page = await ctx.new_page()
        await page.goto(BASE, wait_until="networkidle")
        await page.wait_for_selector(".tab")
        await page.add_style_tag(content="#rain{display:none!important}")  # crisp, no rain
        await settle(page, 1000)
        await shot(page, "01-overview")

        await tab(page, "inspector")
        await settle(page, 1200)                       # inspect auto-runs
        await shot(page, "02-inspector")

        await tab(page, "builder")
        await page.click("#sample")
        await page.click("#analyze")
        await settle(page, 600)
        await shot(page, "03-ingest")

        await tab(page, "integrate")
        await shot(page, "04-integrate")

        await tab(page, "memory")
        await settle(page, 800)
        await shot(page, "05-memory")

        await tab(page, "experts")
        await shot(page, "06-experts")

        await tab(page, "routing")
        await page.click("#run")
        await settle(page, 800)
        await shot(page, "07-routing")

        await tab(page, "benchmarks")
        await shot(page, "08-benchmarks")

        await tab(page, "standard")
        await shot(page, "09-standard")

        await tab(page, "settings")
        await shot(page, "10-settings")

        await browser.close()
    print("done ->", OUT)


if __name__ == "__main__":
    asyncio.run(main())
