from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.skipif(
    not Path("runs/matcher/best.pt").exists(), reason="Requires trained CUFS checkpoint"
)
def test_real_dataset_demo_ranks_gallery():
    app = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "app.py", default_timeout=40
    ).run()
    assert not app.exception
    assert "Sketch2Face" in app.title[0].value
    app.button[0].click().run()
    assert not app.exception
    assert any("Correct photo appears at rank" in message.value for message in app.info)


@pytest.mark.skipif(
    not Path("runs/matcher/best.pt").exists(), reason="Requires trained CUFS checkpoint"
)
def test_upload_mode_loads_without_data():
    app = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "app.py", default_timeout=40
    ).run()
    app.radio[0].set_value("Upload images").run()
    assert not app.exception
