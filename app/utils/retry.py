"""Retry helpers built on tenacity."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

T = TypeVar("T")

DEFAULT_RETRY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
)


def _before_sleep(retry_state: Any) -> None:
    outcome = retry_state.outcome
    exception = outcome.exception() if outcome else None
    logger.warning(
        "Retrying {} (attempt {}) after failure: {}",
        getattr(retry_state.fn, "__name__", "task"),
        retry_state.attempt_number,
        exception,
    )


def retry_async(
    attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[type[BaseException], ...] = DEFAULT_RETRY_EXCEPTIONS,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry decorator for async functions with exponential backoff."""
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
        before_sleep=_before_sleep,
    )
