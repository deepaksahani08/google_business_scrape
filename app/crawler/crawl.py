"""Crawl one business website for public email addresses."""

from __future__ import annotations

from loguru import logger

from app.config import Config
from app.crawler import contact as contact_crawler
from app.crawler import email as email_extractor
from app.crawler.website import WebsiteFetcher
from app.schemas import Business
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
