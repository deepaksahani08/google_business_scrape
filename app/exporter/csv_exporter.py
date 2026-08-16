"""Incremental CSV export using pandas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from app.config import Config

CSV_COLUMNS = ["Company Name", "Phone", "Website", "Email", "Address", "Source", "Source URL"]


class CsvExporter:
    """Buffers business rows and appends them to the CSV incrementally."""

    def __init__(self, config: Config, output_path: Path | None = None) -> None:
        self.config = config
        self.path = output_path or (config.output_dir / "results.csv")
        self._buffer: list[dict[str, str]] = []
        self._seen_urls: set[str] = set()
        self._header_written = self.path.exists() and self.path.stat().st_size > 0
        self._written = 0

    def write(self, row: dict[str, str]) -> None:
        """Queue a row; flush when the buffer reaches the configured size."""
        key = self._row_key(row)
        if key in self._seen_urls:
            logger.debug("Skipping duplicate row for {}", key)
            return
        self._seen_urls.add(key)
        self._buffer.append({column: row.get(column, "") for column in CSV_COLUMNS})
        if len(self._buffer) >= self.config.email_flush_size:
            self.flush()

    @staticmethod
    def _row_key(row: dict[str, str]) -> str:
        """Stable dedup key: source + source URL, falling back to the name."""
        source = row.get("Source", "")
        url = row.get("Source URL", "")
        if url:
            return f"{source}|{url}"
        return f"{source}|{row.get('Company Name', '')}"

    def flush(self) -> None:
        """Write buffered rows to the CSV file (append mode)."""
        if not self._buffer:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(self._buffer)
        frame.to_csv(
            self.path,
            mode="a",
            header=not self._header_written,
            index=False,
            encoding="utf-8",
        )
        self._written += len(self._buffer)
        self._header_written = True
        logger.debug("Flushed {} row(s) to {}", len(self._buffer), self.path)
        self._buffer.clear()

    def close(self) -> None:
        """Flush any remaining rows and log a summary."""
        self.flush()
        logger.info("CSV export complete: {} row(s) written to {}", self._written, self.path)
