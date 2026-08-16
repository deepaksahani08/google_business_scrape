"""Entry point for the Business Scraper (Google Maps / DuckDuckGo).

Run with:

    python -m app.main "dentist" "Dallas, TX"
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

from loguru import logger

from app.config import Config
from app.crawler import contact as contact_crawler
from app.crawler import email as email_extractor
from app.crawler.website import WebsiteFetcher
from app.exporter.csv_exporter import CsvExporter
from app.scraper import duckduckgo
from app.scraper import google_maps
from app.scraper.browser import BrowserSession
from app.schemas import Business
from app.utils.logger import setup_logging
from app.utils.urls import build_candidate_pages


async def crawl_website_for_emails(
    business: Business,
    fetcher: WebsiteFetcher,
    config: Config,
) -> None:
    """Crawl the business website and populate ``business.emails`` in place."""
    candidates = build_candidate_pages(business.website, config)
    fetched = await fetcher.fetch_pages(candidates)

    home_html = fetched.get(candidates[0], "") if candidates else ""
    if home_html:
        discovered = contact_crawler.discover_contact_pages(home_html, candidates[0], config)
        extra = [url for url in discovered if url not in fetched]
        if extra:
            logger.debug("Discovered {} additional page(s) for {}", len(extra), business.name)
            fetched.update(await fetcher.fetch_pages(extra))

    business.emails = email_extractor.extract_emails_from_pages(fetched)
    logger.info(
        "Business '{}': {} email(s) found",
        business.name or business.website,
        len(business.emails),
    )


async def process_ddg_business(
    business: Business,
    fetcher: WebsiteFetcher,
    config: Config,
) -> Business:
    """Run the pipeline for one DuckDuckGo-sourced business (name + website)."""
    if business.website:
        await crawl_website_for_emails(business, fetcher, config)
    else:
        logger.info("No website for '{}' - skipping crawl", business.name)
    return business


async def process_maps_business(
    maps_url: str,
    browser: BrowserSession,
    fetcher: WebsiteFetcher,
    config: Config,
) -> Business:
    """Run the full pipeline for one Google Maps place URL."""
    page_html = await browser.fetch_html(maps_url)
    business = google_maps.parse_place_page(page_html, maps_url)
    logger.info(
        "Parsed Google Maps place: {} (website: {})",
        business.name or maps_url,
        business.website or "none",
    )
    if business.website:
        await crawl_website_for_emails(business, fetcher, config)
    return business


@asynccontextmanager
async def _browser_if_needed(config: Config):
    """Yield a BrowserSession only when a browser-based platform is required."""
    if config.search_source == "google_maps":
        async with BrowserSession(config) as browser:
            yield browser
    else:
        yield None


async def run(
    category: str,
    location: str,
    config: Config,
    output_path: Path | None = None,
) -> int:
    """Orchestrate the full scraping pipeline and return the number of items."""
    setup_logging(config)
    source = config.search_source
    logger.info(
        "Scraper starting: category='{}' location='{}' source='{}'",
        category,
        location,
        source,
    )

    exporter = CsvExporter(config, output_path=output_path)
    semaphore = asyncio.Semaphore(config.concurrency)

    async def run_one_duckduckgo(business: Business) -> None:
        async with semaphore:
            try:
                await process_ddg_business(business, fetcher, config)
                exporter.write(business.to_csv_row())
            except Exception as exc:  # noqa: BLE001 - keep the run going
                logger.error(
                    "Failed to process {}: {}",
                    business.name or business.website,
                    exc,
                )

    async def run_one_maps(maps_url: str) -> None:
        async with semaphore:
            try:
                business = await process_maps_business(maps_url, browser, fetcher, config)
                exporter.write(business.to_csv_row())
            except Exception as exc:  # noqa: BLE001 - keep the run going
                logger.error("Failed to process {}: {}", maps_url, exc)

    async with _browser_if_needed(config) as browser, WebsiteFetcher(config) as fetcher:
        maps_urls: list[str] = []
        ddg_businesses: list[Business] = []

        if source == "google_maps":
            assert browser is not None
            maps_urls = await google_maps.collect_business_urls(browser, config, category, location)
        elif source == "duckduckgo":
            ddg_businesses = await duckduckgo.search_businesses(category, location, config)
        else:  # pragma: no cover - validated by CLI/UI
            logger.error("Unknown search source: '{}'", source)

        total = len(maps_urls) + len(ddg_businesses)
        logger.info(
            "Collected {} business item(s) ({} Google Maps, {} DuckDuckGo)",
            total,
            len(maps_urls),
            len(ddg_businesses),
        )

        tasks = [run_one_maps(url) for url in maps_urls]
        tasks += [run_one_duckduckgo(business) for business in ddg_businesses]
        await asyncio.gather(*tasks)

    exporter.close()
    logger.info("Pipeline finished: {} item(s) processed", total)
    return total


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Business Scraper (Google Maps / DuckDuckGo)"
    )
    parser.add_argument("category", help="Business category, e.g. 'dentist'")
    parser.add_argument("location", help="Location, e.g. 'Dallas, TX'")
    parser.add_argument(
        "--output",
        default=None,
        help="CSV output path (default: output/results.csv)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Override the concurrency level",
    )
    parser.add_argument(
        "--source",
        choices=["google_maps", "duckduckgo"],
        default=None,
        help="Search source: 'google_maps' (default) or 'duckduckgo'",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = Config()
    if args.concurrency is not None:
        config = replace(config, concurrency=args.concurrency)
    if args.source is not None:
        config = replace(config, search_source=args.source)
    output_path = Path(args.output) if args.output else None

    count = asyncio.run(run(args.category, args.location, config, output_path))

    default_path = config.output_dir / "results.csv"
    final_path = output_path or default_path
    print(f"Done: {count} business(es) processed. CSV written to {final_path}")


if __name__ == "__main__":
    main()
