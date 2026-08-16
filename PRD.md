# PRD.md

# Business Scraper MVP

## Version

MVP v1.3

v1.1 added a Streamlit web UI and a DuckDuckGo search source.
v1.2 added a Google Maps platform: Google Maps is scraped directly with the
browser (no API key), and the UI exposes a platform dropdown.
v1.3 removes the Yelp platform: Yelp search, pagination, and parsing code
are deleted and the platform dropdown is now google_maps / duckduckgo.
Google Maps is the default source and the Google Maps result limit defaults
to 60 (UI slider allows up to 200).

---

# Objective

Create a lightweight Python scraper that searches Google Maps (or DuckDuckGo) using a
business category and location, extracts business information, crawls each
company's website for publicly available email addresses, and exports the
results to a CSV file.

The project prioritizes simplicity, reliability, and maintainability over feature completeness.

---

# Tech Stack (Frozen)

Python 3.13+

Playwright (Google Maps browsing)

AsyncIO

HTTPX (company websites only)

selectolax (HTML parsing)

Regex (email extraction)

pandas

tenacity

python-dotenv

loguru

Streamlit (web UI)

duckduckgo-search (DuckDuckGo search source)

No other libraries should be introduced unless absolutely required to fix a bug.

---

# Excluded (Frozen)

Databases

APIs

FastAPI

Docker

Proxy Rotation

CAPTCHA Solving

AI Features

Email Verification

LinkedIn

CRM Integrations

n8n

---

# Folder Structure (Frozen)

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
│   │   ├── __init__.py
│   │   ├── website.py
│   │   ├── contact.py
│   │   └── email.py
│   │
│   ├── exporter/
│   │   ├── __init__.py
│   │   └── csv_exporter.py
│   │
│   └── utils/
│       ├── __init__.py
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

This structure is frozen for MVP.

All Python modules live under `app/`. No folder may be renamed, moved, or have new layers added.

---

# Functional Requirements

## Input

Business Category

Location

Example:

Dentist

Dallas, TX

---

## Google Maps Search

Open Google Maps search (no API key)

Scroll the results feed

Collect business place URLs

If Google Maps blocks automated access, stop gracefully

---

## Business Extraction

For every business collect:

Business Name

Phone Number

Website URL

Business Address

Source URL (Google Maps place URL; DuckDuckGo result URL)

Source (google_maps / duckduckgo)

---

## Website Crawling

Visit the company website.

Search only a limited number of pages.

Allowed pages include:

/

/contact

/contact-us

/about

/about-us

/company

/team

/support

/privacy

---

## Email Extraction

Extract emails using Regex.

Remove duplicates.

Ignore placeholder emails such as:

example@example.com

test@test.com

noreply@

localhost

---

## DuckDuckGo Source (optional)

DuckDuckGo is available as an explicit search source.

Collect from DuckDuckGo results:

Business Name

Website URL

Source URL, Phone, and Address are left empty for DuckDuckGo-sourced results.

---

## Web UI (Streamlit)

Streamlit app at `app/ui.py` (run with `streamlit run app/ui.py`).

Inputs:

Business Category

Location

Platform (google_maps / duckduckgo)

Run the scraper from the UI.

Preview results in a table.

Download the CSV.

---

## Output

CSV columns:

Company Name

Phone

Website

Email

Address

Source

Source URL

---

# Non-Functional Requirements

Async execution

Retry failed requests

Structured logging

Incremental CSV writing

Graceful error handling

Configurable concurrency

---

# Environment Variables (.env)

CONCURRENCY

Maximum number of concurrent business pipelines (default 5)

HEADLESS

Run the Playwright browser headless (true/false, default true)

LOG_LEVEL

Logging level (DEBUG, INFO, WARNING, ERROR, default INFO)

BROWSER_TIMEOUT_MS

Navigation timeout in milliseconds (default 30000)

HTTP_TIMEOUT_SEC

Company website request timeout in seconds (default 15)

REQUEST_DELAY_SEC

Politeness delay between website requests in seconds (default 1.0)

SEARCH_SOURCE

Search source: google_maps or duckduckgo (default google_maps)

DDG_MAX_RESULTS

Maximum number of DuckDuckGo results (default 15)

DDG_REGION

DuckDuckGo region code (default us-en)

GOOGLE_MAPS_MAX_RESULTS

Maximum number of Google Maps results to collect (default 60; UI slider allows up to 200)

---

# Development Phases

Phase 1

Project setup

Folder structure

---

Phase 2

Configuration

Logging

---

Phase 3

Playwright browser

---

Phase 4

Google Maps search

Scroll the results feed

Collect business place URLs

---

Phase 5

Business parser

Extract business information

---

Phase 6

Website crawler

Discover contact pages

---

Phase 7

Email extractor

Regex

Deduplication

---

Phase 8

CSV exporter

Incremental writing

---

Phase 9

End-to-end testing

Run the full pipeline

Validate the CSV output

---

Phase 10 (v1.1)

Web UI (Streamlit)

DuckDuckGo search source

---

Phase 11 (v1.2)

Google Maps platform (direct browser scraping, no API key)

Platform dropdown

---

Phase 12 (v1.3)

Remove Yelp platform (code and dropdown)

Google Maps is the default source

Google Maps result limit default 60, UI slider up to 200

---

# Definition of Done

The application accepts:

Category

Location

Produces a CSV containing:

Company Name

Phone

Website

Email

Address

Source

Source URL

No databases or additional integrations are included in MVP v1.3.

MVP v1.3 provides a Streamlit web UI, a DuckDuckGo search source, and a
Google Maps platform (direct browser scraping, no API key). The Yelp
platform has been removed.
