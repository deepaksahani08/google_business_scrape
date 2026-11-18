"""Small shared helpers for text cleaning and email filtering."""

from __future__ import annotations

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
