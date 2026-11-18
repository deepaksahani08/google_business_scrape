"""Web server for the Google Maps scraper, used by the Vercel container.

Run with:

    python -m app.web
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from loguru import logger

from app.config import BASE_DIR, Config
from app.crawler.crawl import crawl_website_for_emails
from app.crawler.website import WebsiteFetcher
from app.schemas import Business
from app.scraper import google_maps
from app.scraper.browser import BrowserSession

INDEX_PATH: Path = BASE_DIR / "public" / "index.html"

#: Stop before Vercel's 300-second function limit so partial results still return.
TIME_BUDGET_SEC = 240.0
COLLECT_TIMEOUT_SEC = 75.0
MAX_BODY_BYTES = 4096
MAX_TEXT_LENGTH = 100
MAX_RESULTS_LIMIT = 50
DEFAULT_RESULTS = 20

#: Chromium is memory hungry, so each instance runs one scrape at a time.
_SCRAPE_SLOT = threading.BoundedSemaphore(1)


class BadRequest(ValueError):
    """The request body failed validation."""


def parse_request(raw_body: bytes) -> tuple[str, str, int]:
    """Validate the JSON body and return ``(category, location, max_results)``."""
    try:
        body = json.loads(raw_body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BadRequest("The request body must be valid JSON.") from exc
    if not isinstance(body, dict):
        raise BadRequest("The request body must be a JSON object.")

    category = _clean_text(body.get("category"), "category")
    location = _clean_text(body.get("location"), "location")

    max_results = body.get("max_results", DEFAULT_RESULTS)
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise BadRequest("max_results must be a whole number.")
    if not 1 <= max_results <= MAX_RESULTS_LIMIT:
        raise BadRequest(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}.")
    return category, location, max_results


def _clean_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BadRequest(f"{field} is required.")
    cleaned = value.strip()
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise BadRequest(f"{field} must be {MAX_TEXT_LENGTH} characters or fewer.")
    return cleaned


async def _collect_urls(
    browser: BrowserSession,
    config: Config,
    category: str,
    location: str,
) -> list[str]:
    """Collect place URLs, treating a slow search as no results."""
    try:
        return await asyncio.wait_for(
            google_maps.collect_business_urls(browser, config, category, location),
            timeout=COLLECT_TIMEOUT_SEC,
        )
    except TimeoutError:
        logger.warning("Google Maps search timed out for '{} in {}'", category, location)
        return []


async def scrape(category: str, location: str, max_results: int) -> dict:
    """Scrape Google Maps, returning whatever finishes within the time budget."""
    deadline = time.monotonic() + TIME_BUDGET_SEC
    config = replace(
        Config(),
        google_maps_max_results=max_results,
        headless=True,
        concurrency=3,
        request_delay_sec=0.2,
        http_timeout_sec=8.0,
        browser_timeout_ms=20000,
    )
    businesses: list[Business] = []
    slots = asyncio.Semaphore(config.concurrency)

    async with BrowserSession(config) as browser, WebsiteFetcher(config) as fetcher:
        async def process_place(url: str) -> None:
            async with slots:
                html = await browser.fetch_html(url)
                business = google_maps.parse_place_page(html, url)
                if not business.name:
                    return
                businesses.append(business)
                if business.website:
                    await crawl_website_for_emails(business, fetcher, config)

        urls = await _collect_urls(browser, config, category, location)
        tasks = [asyncio.create_task(process_place(url)) for url in urls]
        pending: set[asyncio.Task] = set()
        if tasks:
            timeout = max(deadline - time.monotonic(), 1.0)
            _, pending = await asyncio.wait(tasks, timeout=timeout)
            for task in pending:
                task.cancel()
            for outcome in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(outcome, Exception):
                    logger.warning("Google Maps place failed: {}", outcome)

    return {
        "count": len(businesses),
        "unfinished": len(pending),
        "results": [business.to_csv_row() for business in businesses],
    }


class Handler(BaseHTTPRequestHandler):
    """Serve the web page and ``POST /api/scrape``."""

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlsplit(self.path).path
        if path == "/api/scrape":
            self._send_bytes(405, b"", "text/plain", {"Allow": "POST"})
        elif path in {"/", "/index.html"}:
            self._send_bytes(200, INDEX_PATH.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if urlsplit(self.path).path != "/api/scrape":
            self._send_json(404, {"error": "Not found."})
            return
        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length header."})
            return
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "The request is too large."})
            return
        try:
            category, location, max_results = parse_request(self.rfile.read(length))
        except BadRequest as exc:
            self._send_json(400, {"error": str(exc)})
            return
        if not _SCRAPE_SLOT.acquire(blocking=False):
            self._send_json(429, {"error": "Another search is running. Please try again shortly."})
            return
        try:
            payload = asyncio.run(scrape(category, location, max_results))
        except Exception:  # noqa: BLE001 - never leak internals to the client
            logger.exception("Scrape request failed")
            self._send_json(500, {"error": "The scrape failed. Please try again."})
        else:
            self._send_json(200, payload)
        finally:
            _SCRAPE_SLOT.release()

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.getenv("PORT", "80"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    logger.info("Serving on port {}", port)
    server.serve_forever()


if __name__ == "__main__":
    main()
