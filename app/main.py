"""Entry point for the Google Maps Business Scraper.

Run with:

    python -m app.main "dentist" "Dallas, TX"
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from loguru import logger

from app.config import Config
from app.crawler.crawl import crawl_website_for_emails
from app.crawler.website import WebsiteFetcher
from app.exporter.csv_exporter import CsvExporter
from app.scraper import google_maps
from app.scraper.browser import BrowserSession
from app.schemas import Business
from app.utils.logger import setup_logging


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


async def run(
    category: str,
    location: str,
    config: Config,
    output_path: Path | None = None,
) -> int:
    """Orchestrate the full scraping pipeline and return the number of items."""
    setup_logging(config)
    logger.info("Scraper starting: category='{}' location='{}'", category, location)

    exporter = CsvExporter(config, output_path=output_path)
    semaphore = asyncio.Semaphore(config.concurrency)

    async def run_one_maps(maps_url: str) -> None:
        async with semaphore:
            try:
                business = await process_maps_business(maps_url, browser, fetcher, config)
                exporter.write(business.to_csv_row())
            except Exception as exc:  # noqa: BLE001 - keep the run going
                logger.error("Failed to process {}: {}", maps_url, exc)

    async with BrowserSession(config) as browser, WebsiteFetcher(config) as fetcher:
        maps_urls = await google_maps.collect_business_urls(browser, config, category, location)
        total = len(maps_urls)
        logger.info("Collected {} Google Maps business(es)", total)
        await asyncio.gather(*(run_one_maps(url) for url in maps_urls))

    exporter.close()
    logger.info("Pipeline finished: {} item(s) processed", total)
    return total


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Maps Business Scraper")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = Config()
    if args.concurrency is not None:
        config = replace(config, concurrency=args.concurrency)
    output_path = Path(args.output) if args.output else None

    count = asyncio.run(run(args.category, args.location, config, output_path))

    default_path = config.output_dir / "results.csv"
    final_path = output_path or default_path
    print(f"Done: {count} business(es) processed. CSV written to {final_path}")


if __name__ == "__main__":
    main()
