"""Temp verification: Google Maps parsing (offline) + live collection check."""
import asyncio
import os
from pathlib import Path

import pandas as pd

from app.config import Config
from app.exporter.csv_exporter import CsvExporter
from app.schemas import Business
from app.scraper import google_maps
from app.scraper.browser import BrowserSession

PLACE_FIXTURE = """
<html><body>
  <h1>City Dental Dallas</h1>
  <button data-item-id="address">\ue0c8 123 Main St, Dallas, TX 75201</button>
  <button data-item-id="phone:tel:+1-214-555-0100">\ue0b0 (214) 555-0100</button>
  <a data-item-id="authority" href="https://citydentaldallas.com/?utm_source=Google&utm_medium=Organic">Website</a>
</body></html>
"""


def test_build_search_url():
    url = google_maps.build_search_url("dentist", "Dallas, TX")
    assert url == "https://www.google.com/maps/search/dentist%20in%20Dallas%2C%20TX", url
    print("build_search_url OK:", url)


def test_parse_place_page():
    business = google_maps.parse_place_page(
        PLACE_FIXTURE, "https://www.google.com/maps/place/City+Dental"
    )
    assert business.name == "City Dental Dallas", business.name
    assert business.phone == "(214) 555-0100", business.phone
    assert business.website == "https://citydentaldallas.com/", business.website
    assert business.address == "123 Main St, Dallas, TX 75201", business.address
    assert business.source == "google_maps", business.source
    assert business.source_url == "https://www.google.com/maps/place/City+Dental"
    print("parse_place_page OK:", business.to_csv_row())


def test_extract_place_links():
    html = """
    <div role="feed">
      <a href="https://www.google.com/maps/place/City+Dental/@32.7,-96.7,17z">card1</a>
      <a href="https://www.google.com/maps/place/Smile+Clinic/@32.8,-96.8,17z?authuser=0">card2</a>
      <a href="https://www.google.com/maps/place/City+Dental/@32.7,-96.7,17z">dup</a>
      <a href="https://www.yelp.com/biz/other">not a maps link</a>
    </div>
    """
    links = google_maps.extract_place_links(html)
    assert len(links) == 2, links
    assert "?" not in links[1], links
    print("extract_place_links OK:", links)


def test_csv_columns_and_dedup():
    tmp = Path("output/_gm_check.csv")
    if tmp.exists():
        tmp.unlink()
    config = Config()
    exporter = CsvExporter(config, output_path=tmp)
    exporter.write(Business(name="Alpha Dental", source="duckduckgo").to_csv_row())
    exporter.write(Business(name="Beta Dental", source="duckduckgo").to_csv_row())
    exporter.write(Business(name="Alpha Dental", source="duckduckgo").to_csv_row())  # dupe
    exporter.write(
        Business(name="City Dental", source="google_maps", source_url="https://gm/place/C").to_csv_row()
    )
    exporter.close()
    df = pd.read_csv(tmp)
    expected = ["Company Name", "Phone", "Website", "Email", "Address", "Source", "Source URL"]
    assert list(df.columns) == expected, list(df.columns)
    assert len(df) == 3, len(df)
    sources = set(df["Source"])
    assert sources == {"duckduckgo", "google_maps"}, sources
    print("csv exporter OK:", list(df.columns), "rows:", len(df), "sources:", sources)
    tmp.unlink()


def test_schema_row():
    row = Business(
        name="X", source="google_maps", source_url="https://www.google.com/maps/place/X"
    ).to_csv_row()
    assert row["Source"] == "google_maps" and row["Source URL"] == "https://www.google.com/maps/place/X", row
    print("schema row OK:", row)


def test_strip_tracking():
    url = google_maps._strip_tracking_params(
        "https://www.parkcentraldentaltx.com/?utm_source=Google&utm_medium=Organic&gclid=abc&page=2"
    )
    assert url == "https://www.parkcentraldentaltx.com/?page=2", url
    print("strip tracking OK:", url)


async def test_live():
    config = Config()
    async with BrowserSession(config) as browser:
        urls = await google_maps.collect_business_urls(browser, config, "dentist", "Dallas, TX")
        print(f"live Google Maps returned {len(urls)} place URL(s)")
        for u in urls[:5]:
            print("  -", u)
        if urls:
            html = await browser.fetch_html(urls[0])
            business = google_maps.parse_place_page(html, urls[0])
            print("  first place parsed:", business)


if __name__ == "__main__":
    test_build_search_url()
    test_parse_place_page()
    test_extract_place_links()
    test_csv_columns_and_dedup()
    test_schema_row()
    test_strip_tracking()
    asyncio.run(test_live())
