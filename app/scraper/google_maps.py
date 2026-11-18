"""Google Maps business search - no API key, driven with the Playwright browser.

Google Maps renders search results client-side and paginates by infinite
scroll, so we drive the browser directly:

1. Open the Google Maps search feed for "<category> in <location>".
2. Scroll through the feed and collect unique business "place" URLs.
3. Each place URL is later fetched by the pipeline and parsed with
   ``parse_place_page`` for name, phone, website, and address.

No Google Maps API key is required.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from loguru import logger
from selectolax.parser import HTMLParser

from app.config import Config
from app.schemas import Business
from app.scraper.browser import BrowserSession
from app.utils.helpers import dedupe_preserve_order, format_us_phone, normalize_whitespace

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/{}"

#: The results feed renders one business "card" per place; each card links to
#: its place page. ``div[role='feed']`` wraps the list of search results.
_FEED_SELECTOR = "div[role='feed']"
_PLACE_LINK_SELECTOR = "div[role='feed'] a[href*='/maps/place/']"
_ANY_PLACE_LINK_SELECTOR = "a[href*='/maps/place/']"

#: Best-effort selectors for the Google consent banner (EEA users).
_CONSENT_SELECTORS = (
    "button[aria-label*='Accept all']",
    "button[jsaction*='consent']",
)

#: Markers that indicate Google served an anti-bot challenge instead of results.
_CHALLENGE_MARKERS = (
    "unusual traffic",
    "recaptcha",
    "captcha",
    "enable cookies",
)

#: Private-use-area / control characters that leak into button text as
#: Material-icon glyphs (e.g. the call and location icons on place pages).
_ICON_PATTERN = re.compile(r"[\ue000-\uf8ff\ufdd0-\ufdef\ufff0-\uffff]")

#: Tracking query parameters stripped from outbound website links.
_TRACKING_QUERY_KEYS = {"gclid", "fbclid", "yclid"}


def _clean_text(text: str) -> str:
    """Strip Material-icon glyphs and collapse whitespace in extracted text."""
    return normalize_whitespace(_ICON_PATTERN.sub("", text))


def _strip_tracking_params(url: str) -> str:
    """Remove common tracking query parameters (utm_*, gclid, fbclid, ...)."""
    parsed = urlparse(url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.startswith("utm_") and key not in _TRACKING_QUERY_KEYS
    ]
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(kept), parsed.fragment)
    )


def build_search_url(category: str, location: str) -> str:
    """Build the Google Maps search URL for a category and location."""
    return GOOGLE_MAPS_SEARCH_URL.format(quote(f"{category} in {location}"))


def is_challenge_page(html: str) -> bool:
    """Return True when the page is an anti-bot challenge instead of results."""
    lowered = html.lower()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def extract_place_links(html: str) -> list[str]:
    """Extract unique Google Maps place URLs from a rendered search page."""
    parser = HTMLParser(html)
    links: list[str] = []
    for node in parser.css(_ANY_PLACE_LINK_SELECTOR):
        href = node.attributes.get("href", "")
        if not href or "google.com/maps/place/" not in href:
            continue
        links.append(href.split("?")[0])
    return dedupe_preserve_order(links)


def parse_place_page(html: str, place_url: str) -> Business:
    """Parse a Google Maps place page into a Business object.

    Uses the stable ``data-item-id`` markers on place pages: the address,
    phone, and website elements carry ``address``, ``phone:tel:...``, and
    ``authority`` values respectively.
    """
    tree = HTMLParser(html)
    business = Business(source="google_maps", source_url=place_url)

    name_node = tree.css_first("h1")
    if name_node:
        business.name = _clean_text(name_node.text(strip=True))

    address_node = tree.css_first("button[data-item-id='address']")
    if address_node:
        business.address = _clean_text(address_node.text(strip=True))

    phone_node = tree.css_first("button[data-item-id^='phone:tel:']")
    if phone_node:
        business.phone = format_us_phone(_clean_text(phone_node.text(strip=True)), business.address)

    site_node = tree.css_first("a[data-item-id='authority']")
    if site_node:
        business.website = _strip_tracking_params(site_node.attributes.get("href", ""))

    return business


async def _accept_consent(page) -> None:
    """Best-effort dismissal of the Google consent banner, if present."""
    for selector in _CONSENT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() > 0:
                await locator.click(timeout=3000)
                logger.debug("Accepted Google consent banner")
                return
        except Exception:  # noqa: BLE001 - consent handling is best-effort
            logger.debug("Consent banner not actionable for selector '{}'", selector)


async def collect_business_urls(
    browser: BrowserSession,
    config: Config,
    category: str,
    location: str,
) -> list[str]:
    """Scroll the Google Maps search feed and return unique place URLs."""
    url = build_search_url(category, location)
    logger.info("Opening Google Maps search: {}", url)

    collected: list[str] = []
    known: set[str] = set()

    async with browser.new_page() as page:
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=config.browser_timeout_ms,
            )
        except Exception as exc:  # noqa: BLE001 - graceful failure
            logger.warning("Google Maps navigation failed: {}", exc)
            return []
        await _accept_consent(page)

        try:
            await page.wait_for_selector(_FEED_SELECTOR, timeout=config.browser_timeout_ms)
        except Exception:  # noqa: BLE001 - handled below
            logger.warning(
                "Google Maps search feed not found for '{} in {}' "
                "(likely blocked or no results)",
                category,
                location,
            )
            return []

        # Give lazy-loaded cards time to render after the feed appears.
        await page.wait_for_timeout(2000)

        for step in range(config.google_maps_max_results + 10):
            hrefs = await page.eval_on_selector_all(
                _PLACE_LINK_SELECTOR,
                "els => els.map(e => e.href)",
            )
            fresh = 0
            for href in hrefs:
                if not href or "google.com/maps/place/" not in href:
                    continue
                clean = href.split("?")[0]
                if clean in known:
                    continue
                known.add(clean)
                collected.append(clean)
                fresh += 1
            logger.info(
                "Google Maps scroll {}: {} unique place link(s)",
                step + 1,
                len(collected),
            )
            if len(collected) >= config.google_maps_max_results:
                break
            if not fresh:
                # Results may still be lazy-loading; give them one more chance
                # before giving up.
                if step == 0:
                    await page.wait_for_timeout(2500)
                else:
                    break
            # The feed scrolls independently of the viewport, so scroll the
            # container itself; wheel the window as a fallback.
            await page.evaluate(
                "document.querySelector('div[role=feed]')?.scrollTo(0, "
                "document.querySelector('div[role=feed]').scrollHeight)"
            )
            await page.mouse.wheel(0, 4000)
            await page.wait_for_timeout(1200)

    logger.info("Google Maps returned {} place URL(s)", len(collected))
    return collected[: config.google_maps_max_results]
