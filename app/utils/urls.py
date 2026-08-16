"""URL helpers for normalizing and resolving website links."""

from __future__ import annotations

from urllib.parse import urlparse

from app.config import Config


def ensure_scheme(url: str) -> str:
    """Prepend ``https://`` when the URL has no explicit scheme."""
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        return f"https://{url}"
    return url


def get_origin(url: str) -> str:
    """Return the ``scheme://netloc`` portion of a URL."""
    parsed = urlparse(ensure_scheme(url))
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def is_same_origin(url: str, origin: str) -> bool:
    """Return True when the URL belongs to the given origin."""
    return bool(origin) and get_origin(url) == origin


def build_candidate_pages(website_url: str, config: Config) -> list[str]:
    """Resolve the allowed contact paths against the website origin."""
    origin = get_origin(website_url)
    if not origin:
        return []
    pages: list[str] = []
    for path in config.allowed_contact_paths:
        pages.append(origin if path == "/" else origin.rstrip("/") + path)
    return pages
