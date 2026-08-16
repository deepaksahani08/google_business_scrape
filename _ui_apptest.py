"""Temp verification: Streamlit UI renders the platform dropdown."""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app/ui.py", default_timeout=30)
at.run()
assert not at.exception, at.exception

labels = [s.label for s in at.selectbox]
assert "Platform" in labels, labels
platform = next(s for s in at.selectbox if s.label == "Platform")
print("Platform options:", platform.options)
assert list(platform.options) == ["google_maps", "duckduckgo"], platform.options
assert platform.value == "google_maps", platform.value

slider_labels = [s.label for s in at.slider]
print("Sliders:", slider_labels)
assert "Max Google Maps results" in slider_labels
assert "Concurrency" in slider_labels

gm_slider = next(s for s in at.slider if s.label == "Max Google Maps results")
print("GM slider min/max/value:", gm_slider.min, gm_slider.max, gm_slider.value)
assert gm_slider.max == 200, gm_slider.max
assert gm_slider.value == 60, gm_slider.value

print("AppTest UI OK")
