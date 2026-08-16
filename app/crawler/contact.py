"""Contact page discovery on a business website."""

from __future__ import annotations

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from app.config import Config
from app.utils.helpers import normalize_whitespace
from app.utils.urls import build_candidate_pages, get_origin, is_same_origin

#: Link-text hints used when discovering additional relevant pages.
_CONTACT_HINTS = ("contact", "about", "team", "company")

_MAX_TOTAL_PAGES = 12  # fixed candidates + a few discovered extras


def discover_contact_pages(home_html: str, home_url: str, config: Config) -> list[str]:
    """Return the allowed pages plus same-site links that look relevant.

    The fixed allowed paths always come first; discovered links are appended
    (deduplicated) as long as the total stays within ``_MAX_TOTAL_PAGES``.
    """
    pages = build_candidate_pages(home_url, config)
    origin = get_origin(home_url)
    parser = HTMLParser(home_html)

    for node in parser.css("a[href]"):
        href = node.attributes.get("href", "")
        text = normalize_whitespace(node.text()).lower()
        if not href or href.lstrip().startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if not any(hint in text for hint in _CONTACT_HINTS):
            continue
        absolute = urljoin(home_url, href)
        if not is_same_origin(absolute, origin):
            continue
        if absolute not in pages:
            pages.append(absolute)
        if len(pages) >= _MAX_TOTAL_PAGES:
            break
    return pages
