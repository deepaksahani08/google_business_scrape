"""Temp verification: Streamlit UI renders the Google Maps controls."""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app/ui.py", default_timeout=30)
at.run()
assert not at.exception, at.exception

assert not at.selectbox, [s.label for s in at.selectbox]

slider_labels = [s.label for s in at.slider]
print("Sliders:", slider_labels)
assert "Max Google Maps results" in slider_labels
assert "Concurrency" in slider_labels

gm_slider = next(s for s in at.slider if s.label == "Max Google Maps results")
print("GM slider min/max/value:", gm_slider.min, gm_slider.max, gm_slider.value)
assert gm_slider.max == 200, gm_slider.max
assert gm_slider.value == 60, gm_slider.value

print("AppTest UI OK")
