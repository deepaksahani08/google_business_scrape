"""Fetch business websites with HTTPX (async, retried, rate-limited)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from loguru import logger

from app.config import Config
from app.utils.retry import retry_async


class WebsiteFetcher:
    """Concurrent fetcher for a business's allowed pages."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "WebsiteFetcher":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.http_timeout_sec),
            follow_redirects=True,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None

    @retry_async(attempts=3)
    async def _get(self, url: str) -> str:
        """Fetch a page and return its text, or '' for 404 responses."""
        assert self._client is not None, "WebsiteFetcher must be used as an async context manager"
        response = await self._client.get(url)
        if response.status_code == 404:
            return ""
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type and not content_type.lower().startswith("text/"):
            return ""
        return response.text

    async def fetch_pages(self, urls: list[str]) -> dict[str, str]:
        """Fetch several pages concurrently; returns ``url -> html`` successes."""
        results: dict[str, str] = {}
        semaphore = asyncio.Semaphore(self.config.concurrency)

        async def fetch_one(url: str) -> None:
            async with semaphore:
                await asyncio.sleep(self.config.request_delay_sec)
                try:
                    html = await self._get(url)
                    results[url] = html
                    logger.debug("Fetched {} ({} bytes)", url, len(html))
                except Exception as exc:  # noqa: BLE001 - keep the crawl going
                    logger.warning("Failed to fetch {}: {}", url, exc)

        await asyncio.gather(*(fetch_one(url) for url in urls))
        return results
