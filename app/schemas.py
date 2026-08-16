"""Core data structures shared across the scraping pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Business:
    """A business found on a source platform, including any discovered emails."""

    name: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    source_url: str = ""
    source: str = "google_maps"
    emails: list[str] = field(default_factory=list)

    def to_csv_row(self) -> dict[str, str]:
        """Serialize the business into a CSV-ready row."""
        return {
            "Company Name": self.name,
            "Phone": self.phone,
            "Website": self.website,
            "Email": "; ".join(self.emails),
            "Address": self.address,
            "Source": self.source,
            "Source URL": self.source_url,
        }
