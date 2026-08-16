"""Email extraction via regex, with deduplication and placeholder filtering."""

from __future__ import annotations

import re

from app.utils.helpers import dedupe_preserve_order, is_placeholder_email

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

#: File-extension style TLDs that indicate email-like strings from asset URLs.
_INVALID_TLDS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "svg",
    "css",
    "js",
    "woff",
    "woff2",
    "ico",
}


def extract_emails(html: str) -> list[str]:
    """Extract, clean, deduplicate and filter email addresses from HTML."""
    found: list[str] = []
    for match in _EMAIL_RE.finditer(html):
        email = match.group(0).rstrip(".")
        domain = email.rsplit("@", 1)[-1].lower()
        if domain.split(".")[-1] in _INVALID_TLDS:
            continue
        if is_placeholder_email(email):
            continue
        found.append(email.lower())
    return dedupe_preserve_order(found)


def extract_emails_from_pages(pages: dict[str, str]) -> list[str]:
    """Extract emails from several fetched pages, deduplicated across pages."""
    emails: list[str] = []
    for html in pages.values():
        emails.extend(extract_emails(html))
    return dedupe_preserve_order(emails)
