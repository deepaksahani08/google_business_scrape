"""Playwright browser management for browser-based scraping."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.config import Config
from app.utils.retry import retry_async


class BrowserSession:
    """Owns a single Playwright browser and yields pages for scraping (Google Maps).

    One browser context is shared; every ``fetch_html`` call creates a private
    page, so concurrent calls are safe.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> "BrowserSession":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=self.config.user_agent,
            locale="en-US",
            viewport={"width": 1366, "height": 768},
        )
        # Mask common automation markers so sites treat us like a normal browser.
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        logger.info("Playwright chromium launched (headless={})", self.config.headless)
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        logger.info("Playwright browser closed")

    @retry_async(attempts=3)
    async def fetch_html(self, url: str) -> str:
        """Navigate to a URL and return the rendered page HTML."""
        assert self._context is not None, "BrowserSession must be used as an async context manager"

        # Small politeness delay between navigations.
        await asyncio.sleep(self.config.request_delay_sec)

        page = await self._context.new_page()
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.config.browser_timeout_ms,
            )
            await page.wait_for_timeout(1500)  # let lazy content render
            return await page.content()
        finally:
            await page.close()

    @asynccontextmanager
    async def new_page(self) -> AsyncIterator[Page]:
        """Yield a private page for interactive scraping (e.g. scrolling).

        The page shares the session's context (cookies, user agent) and is
        closed automatically when the block exits.
        """
        assert self._context is not None, "BrowserSession must be used as an async context manager"
        page = await self._context.new_page()
        try:
            yield page
        finally:
            await page.close()
