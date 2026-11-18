"""Application configuration loaded from environment variables (``.env``)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from the .env file at the project root.
load_dotenv(BASE_DIR / ".env")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    """Frozen configuration for the Business Scraper MVP."""

    concurrency: int = int(os.getenv("CONCURRENCY", "5"))
    headless: bool = _env_bool("HEADLESS", True)
    container_mode: bool = _env_bool("CONTAINER_MODE", False)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    user_agent: str = os.getenv("USER_AGENT", DEFAULT_USER_AGENT)
    browser_timeout_ms: int = int(os.getenv("BROWSER_TIMEOUT_MS", "30000"))
    http_timeout_sec: float = float(os.getenv("HTTP_TIMEOUT_SEC", "15.0"))
    request_delay_sec: float = float(os.getenv("REQUEST_DELAY_SEC", "1.0"))
    email_flush_size: int = int(os.getenv("EMAIL_FLUSH_SIZE", "25"))
    google_maps_max_results: int = int(os.getenv("GOOGLE_MAPS_MAX_RESULTS", "60"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "output")))
    logs_dir: Path = Path(os.getenv("LOGS_DIR", str(BASE_DIR / "logs")))
    allowed_contact_paths: tuple[str, ...] = (
        "/",
        "/contact",
        "/contact-us",
        "/about",
        "/about-us",
        "/company",
        "/team",
        "/support",
        "/privacy",
    )
