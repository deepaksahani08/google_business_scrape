"""DuckDuckGo business search - a non-browser search source.

Uses the ``duckduckgo-search`` package (sync API) executed in a worker
thread so it composes with the async pipeline.
"""

from __future__ import annotations

import asyncio
import re

from duckduckgo_search import DDGS
from loguru import logger

from app.config import Config
from app.schemas import Business
from app.utils.helpers import normalize_whitespace
from app.utils.urls import ensure_scheme

#: Domains that are not business websites and should be filtered out.
_BLOCKED_DOMAINS = (
    "yelp.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "google.com",
    "googleapis.com",
    "maps.",
    "yellowpages.com",
    "tripadvisor.com",
    "angieslist.com",
    "bbb.org",
    "merchantcircle.com",
    "superpages.com",
    "manta.com",
    "hotfrog.com",
    "yell.com",
    "thryv.com",
    "zillow.com",
    "realtor.com",
    "indeed.com",
    "glassdoor.com",
)

#: Title suffixes that indicate a result is not the business's own site.
_TITLE_JUNK = (" | facebook", " | linkedin", " | twitter", " - home")


def _is_blocked(href: str) -> bool:
    lowered = href.lower()
    return any(domain in lowered for domain in _BLOCKED_DOMAINS)


def _clean_title(title: str) -> str:
    cleaned = normalize_whitespace(title)
    for junk in _TITLE_JUNK:
        match = re.search(re.escape(junk), cleaned, flags=re.IGNORECASE)
        if match:
            cleaned = cleaned[: match.start()].strip()
            break
    return cleaned


def _ddgs_text(query: str, max_results: int, region: str) -> list[dict]:
    """Run a DuckDuckGo text search (sync; called via asyncio.to_thread)."""
    with DDGS() as ddgs:
        return list(ddgs.text(query, region=region, max_results=max_results))


def _results_to_businesses(results: list[dict]) -> list[Business]:
    """Convert DuckDuckGo results into Business objects (name + website)."""
    businesses: list[Business] = []
    seen: set[str] = set()
    for result in results:
        href = result.get("href", "")
        title = _clean_title(result.get("title", ""))
        if not href or not title:
            continue
        if _is_blocked(href):
            continue
        website = ensure_scheme(href)
        if website in seen:
            continue
        seen.add(website)
        businesses.append(Business(name=title, website=website, source="duckduckgo"))
    return businesses


async def search_businesses(
    category: str,
    location: str,
    config: Config,
) -> list[Business]:
    """Search DuckDuckGo for businesses and return name/website results."""
    query = f"{category} {location}"
    logger.info("Searching DuckDuckGo for '{}'", query)
    try:
        results = await asyncio.to_thread(
            _ddgs_text,
            query,
            config.ddg_max_results,
            config.ddg_region,
        )
    except Exception as exc:  # noqa: BLE001 - a search failure should not crash the app
        logger.warning("DuckDuckGo search failed: {}", exc)
        return []
    businesses = _results_to_businesses(results)
    logger.info("DuckDuckGo returned {} business result(s)", len(businesses))
    return businesses
