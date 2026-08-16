"""Temp verification: DuckDuckGo filtering (offline) + live search check."""
import asyncio
import sys

from app.config import Config
from app.scraper import duckduckgo


def test_filtering():
    fixtures = [
        {"href": "https://citydentaldallas.com", "title": "City Dental Dallas - Home"},
        {"href": "https://www.yelp.com/biz/city-dental-dallas", "title": "City Dental - Yelp"},
        {"href": "https://www.facebook.com/citydental", "title": "City Dental | Facebook"},
        {"href": "https://maps.google.com/place/citydental", "title": "City Dental - Google Maps"},
        {"href": "https://smileclinic.com/", "title": "Smile Clinic Dallas, TX | Contact Us"},
        {"href": "https://smileclinic.com/", "title": "Smile Clinic (dupe)"},
        {"href": "", "title": "no link"},
    ]
    businesses = duckduckgo._results_to_businesses(fixtures)
    names = [b.name for b in businesses]
    urls = [b.website for b in businesses]
    assert names == ["City Dental Dallas", "Smile Clinic Dallas, TX | Contact Us"], names
    assert urls == ["https://citydentaldallas.com", "https://smileclinic.com/"], urls
    assert businesses[0].name == "City Dental Dallas", businesses[0].name
    print("offline filter test OK:", names)


async def test_live():
    config = Config()
    businesses = await duckduckgo.search_businesses("dentist", "Dallas, TX", config)
    print(f"live DDG search returned {len(businesses)} business(es)")
    for b in businesses[:5]:
        print("  -", b.name, "->", b.website)


if __name__ == "__main__":
    test_filtering()
    asyncio.run(test_live())
