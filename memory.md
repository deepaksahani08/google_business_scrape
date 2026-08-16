# memory.md

# Project Memory

## Project Name

Business Scraper (Google Maps / DuckDuckGo)

## Status

Implementation Complete (all phases + v1.3: Yelp platform removed, Google Maps default)

Offline smoke tests: PASS

Live Google Maps validation: partial. A live headless run for
"dentist in Dallas, TX" collected real place URLs (results feed is
scrolled by its `div[role='feed']` container via JS) and parsed
name/phone/website/address from place pages (Material-icon glyphs and
utm_*/gclid tracking params are stripped from the extracted text/URLs).
The Google Maps result limit defaults to 60 and the UI slider allows up to
200. Google Maps can still serve anti-bot or consent pages on other
networks; the scraper detects a missing results feed and stops gracefully.
URL building, place-link extraction, and place-page parsing are unit-tested
offline.

Live DuckDuckGo validation: limited. The `duckduckgo-search` API returns
0 results from the current environment (likely anti-bot throttling); the
DuckDuckGo result parsing/filtering is unit-tested offline. The pipeline
handles empty DuckDuckGo results gracefully (0 rows, clear log message).

## Known Limitations

* The Yelp platform was removed in v1.3; the scraper no longer depends on
  Yelp markup, Yelp URLs, or Yelp's anti-bot behavior.
* Contact page discovery is intentionally limited to a small fixed set of
  paths plus a few links found on the homepage.
* Google Maps can also serve anti-bot/CAPTCHA or consent pages to automated
  browsers; the pipeline stops gracefully when the results feed is missing.
* DuckDuckGo can also throttle/block automated search (0 results observed
  in the current environment); the pipeline handles this gracefully.

## Goal

Build an MVP scraper for Google Maps and DuckDuckGo that collects business information and public email addresses from company websites.

## Frozen Tech Stack

* Python 3.13+
* Playwright (Google Maps browsing)
* AsyncIO
* HTTPX (company websites only)
* selectolax (HTML parsing)
* Regex (email extraction)
* pandas
* tenacity
* python-dotenv
* loguru
* Streamlit (web UI)
* duckduckgo-search (DuckDuckGo search source)

Do not replace these technologies unless fixing a blocking bug.

## Frozen Folder Structure

Use only the agreed folder structure.

```text
yelp-scraper/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── schemas.py
│   ├── ui.py
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── browser.py
│   │   ├── duckduckgo.py
│   │   └── google_maps.py
│   │
│   ├── crawler/
│   │   ├── website.py
│   │   ├── contact.py
│   │   └── email.py
│   │
│   ├── exporter/
│   │   └── csv_exporter.py
│   │
│   └── utils/
│       ├── logger.py
│       ├── retry.py
│       ├── urls.py
│       └── helpers.py
│
├── output/
├── logs/
│
├── requirements.txt
├── README.md
└── .env
```

Do not rename folders.

Do not move modules.

Do not introduce new architectural layers.

## Coding Principles

Keep functions small.

Prefer composition over complexity.

Avoid premature optimization.

Write readable code.

Use async where appropriate.

No unnecessary abstractions.

## Scope

Included

* Google Maps Search (direct browser scraping, no API key)
* Infinite-scroll result collection
* Business Details
* Website Crawl
* Contact Page Discovery
* Email Extraction
* CSV Export
* DuckDuckGo Search
* Web UI (Streamlit)

Excluded

* Database
* FastAPI
* Docker
* AI
* Proxy Rotation
* Captcha Solving
* Email Verification
* CRM
* n8n
* LinkedIn

## Development Order

1. Project Setup

2. Configuration and Logging

3. Browser Management

4. Google Maps Search

5. Scroll-based Result Collection

6. Business Parsing

7. Website Crawler

8. Email Extraction

9. CSV Exporter

10. End-to-End Testing

11. (v1.1) Web UI and DuckDuckGo Search
12. (v1.2) Google Maps Platform and Platform Dropdown
13. (v1.3) Remove Yelp Platform; Google Maps is the default source; Google Maps result limit default 60, UI slider up to 200

Never skip phases.

Complete one phase before starting the next.

## Important Rule

Do not change requirements during implementation.

If a new feature is requested, treat it as a future version instead of modifying the MVP.
