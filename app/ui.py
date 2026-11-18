"""Streamlit web UI for the Business Scraper.

Run with:

    streamlit run app/ui.py

Users enter a business category and location and run the Google Maps pipeline
from the browser. Results are previewed in a table and available as a CSV
download.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import replace
from pathlib import Path

# ``streamlit run app/ui.py`` adds the script's folder (app/) to sys.path,
# not the project root, so pin the root here before importing app.* modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from app.config import Config
from app.main import run

st.set_page_config(page_title="Business Scraper", page_icon="🔍", layout="wide")

st.title("🔍 Business Scraper")
st.caption(
    "Search Google Maps for businesses in a category and location, crawl "
    "their websites for public emails, and export to CSV."
)

with st.form("scraper_form"):
    col1, col2 = st.columns(2)
    category = col1.text_input("Business category", value="dentist")
    location = col2.text_input("Location", value="Dallas, TX")

    col3, col4 = st.columns(2)
    google_maps_max_results = col3.slider("Max Google Maps results", 5, 200, 60)
    concurrency = col4.slider("Concurrency", 1, 10, 5)

    run_button = st.form_submit_button("▶ Run scraper", type="primary")

if run_button:
    if not category.strip() or not location.strip():
        st.error("Please provide both a category and a location.")
        st.stop()

    config = Config()
    config = replace(
        config,
        concurrency=int(concurrency),
        google_maps_max_results=int(google_maps_max_results),
    )
    config.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.output_dir / f"results_{int(time.time())}.csv"

    try:
        with st.status("Running the scraper...", expanded=True) as status:
            st.write(
                f"Searching Google Maps for **{category.strip()}** in **{location.strip()}**..."
            )
            count = asyncio.run(
                run(category.strip(), location.strip(), config, output_path)
            )
            status.update(
                label=f"Done — {count} business(es) processed",
                state="complete",
                expanded=False,
            )
        st.session_state["output_path"] = str(output_path)
        st.session_state["count"] = count
    except Exception as exc:  # noqa: BLE001 - surface failures in the UI
        st.error(f"Run failed: {exc}")
        st.stop()

if "output_path" in st.session_state:
    output_path = Path(st.session_state["output_path"])
    if output_path.exists() and output_path.stat().st_size > 0:
        df = pd.read_csv(output_path)
        st.success(
            f"Processed **{st.session_state['count']}** business(es). "
            f"CSV saved to `{output_path.name}`."
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=output_path.name,
            mime="text/csv",
        )
    else:
        st.warning("The run produced no data (Google Maps may have blocked the scraper).")
