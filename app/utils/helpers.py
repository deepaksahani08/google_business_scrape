"""Small shared helpers for text cleaning and email filtering."""

from __future__ import annotations

import re

#: US states, DC, and territories as they appear in postal addresses.
_US_STATE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR VI GU AS MP".split()
)

#: Area codes that use +1 but belong to Canada or the Caribbean.
_NON_US_AREA_CODES = frozenset(
    "204 226 236 249 250 257 263 289 306 343 354 365 367 368 382 387 403 416 418 428 431 437 "
    "438 450 468 474 506 514 519 548 579 581 584 587 604 613 639 647 672 683 705 709 742 753 "
    "778 780 782 807 819 825 867 873 879 902 905 942 "
    "242 246 264 268 284 345 441 473 649 658 664 721 758 767 784 809 829 849 868 869 876".split()
)

_US_STATE_ZIP_RE = re.compile(r"\b([A-Z]{2})\s+\d{5}(?:-\d{4})?\b")
_US_COUNTRY_RE = re.compile(r"\b(?:United States|USA)\b", re.IGNORECASE)
_US_PHONE_RE = re.compile(
    r"^(?:\+?1[\s.-]*)?\(?([2-9]\d{2})\)?[\s.-]*([2-9]\d{2})[\s.-]*(\d{4})$"
)

#: Domains that are obviously placeholders / examples and must be ignored.
PLACEHOLDER_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "test.org",
    "test.net",
    "domain.com",
    "yourdomain.com",
    "email.com",
    "sentry.com",
    "localhost",
    "example",
    "test",
}

#: Local parts that mark automated/placeholder addresses.
PLACEHOLDER_PREFIXES = (
    "noreply",
    "no-reply",
    "donotreply",
    "no_reply",
    "mailer-daemon",
    "example",
)


def normalize_whitespace(value: str) -> str:
    """Collapse runs of whitespace into single spaces."""
    return " ".join(value.split()).strip()


def dedupe_preserve_order(items: list[str]) -> list[str]:
    """Remove duplicates while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def is_us_address(address: str) -> bool:
    """Return True when an address names the US or ends in a US state and ZIP code."""
    if _US_COUNTRY_RE.search(address):
        return True
    return any(state in _US_STATE_CODES for state in _US_STATE_ZIP_RE.findall(address))


def format_us_phone(phone: str, address: str = "") -> str:
    """Format a US phone number as ``+1 (214) 555-0100``; leave other numbers unchanged.

    The address decides the country. Without one, a formatted number counts as
    US unless its area code belongs to another country that also uses +1.
    """
    match = _US_PHONE_RE.match(phone.strip())
    if not match:
        return phone
    area, exchange, line = match.groups()
    if address:
        is_us = is_us_address(address)
    else:
        is_us = not phone.strip().isdigit() and area not in _NON_US_AREA_CODES
    return f"+1 ({area}) {exchange}-{line}" if is_us else phone


def is_placeholder_email(email: str) -> bool:
    """Return True for example/test/no-reply/localhost style addresses."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return True
    local, _, domain = email.partition("@")
    if not local or not domain:
        return True
    if domain in PLACEHOLDER_DOMAINS:
        return True
    if any(local.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
        return True
    return False
