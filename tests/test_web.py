import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from sketch2face import web


@pytest.fixture
def client():
    return TestClient(web.app)


def image_bytes(size=(64, 64)):
    stream = io.BytesIO()
    Image.new("RGB", size, "#b8a399").save(stream, "PNG")
    return stream.getvalue()


def test_home_and_openapi_contract(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Find the face" in page.text
    assert "/api/match" in client.get("/openapi.json").json()["paths"]
    assert client.get("/static/app.js").status_code == 200


@pytest.mark.parametrize(
    "form,files",
    [
        ({}, []),
        ({"example_id": "a", "gallery_mode": "uploaded"}, []),
        ({"example_id": "a"}, [("sketch", ("query.png", image_bytes(), "image/png"))]),
        (
            {"example_id": "a", "gallery_mode": "dataset"},
            [("gallery", ("photo.png", image_bytes(), "image/png"))],
        ),
    ],
)
def test_reject_ambiguous_or_missing_inputs(client, form, files):
    assert client.post("/api/match", data=form, files=files).status_code == 422


@pytest.mark.parametrize("payload", [b"not an image", image_bytes((16, 16))])
def test_reject_invalid_images(client, payload):
    response = client.post(
        "/api/match",
        data={"gallery_mode": "uploaded"},
        files=[
            ("sketch", ("query.png", payload, "image/png")),
            ("gallery", ("candidate.png", image_bytes(), "image/png")),
        ],
    )
    assert response.status_code == 422


def test_file_size_limit(client):
    response = client.post(
        "/api/match",
        data={"gallery_mode": "uploaded"},
        files=[
            ("sketch", ("query.png", b"x" * (web.MAX_FILE + 1), "image/png")),
            ("gallery", ("candidate.png", image_bytes(), "image/png")),
        ],
    )
    assert response.status_code == 413


def test_missing_model_returns_actionable_error(client, monkeypatch, tmp_path):
    web.trained_model.cache_clear()
    monkeypatch.setattr(web, "CHECKPOINT", tmp_path / "missing.pt")
    response = client.post(
        "/api/match",
        data={"gallery_mode": "uploaded"},
        files=[
            ("sketch", ("query.png", image_bytes(), "image/png")),
            ("gallery", ("candidate.png", image_bytes(), "image/png")),
        ],
    )
    assert response.status_code == 503
    assert "trained model" in response.json()["detail"]
    assert not client.get("/api/status").json()["model_ready"]
    web.trained_model.cache_clear()


@pytest.mark.skipif(not Path("data/manifest.json").exists(), reason="Requires local dataset")
def test_gallery_is_allowlisted(client):
    result = client.get("/api/examples").json()
    assert len(result["examples"]) == 37
    first = result["examples"][0]
    assert client.get(first["photo_url"]).headers["content-type"] == "image/jpeg"
    assert client.get("/api/images/unknown/photo").status_code == 404
    assert client.get("/api/images/unknown/secrets").status_code == 422
    assert client.post("/api/match", data={"example_id": "unknown"}).status_code == 404


@pytest.mark.skipif(not Path("runs/matcher/best.pt").exists(), reason="Requires real checkpoint")
def test_actual_uploaded_images_use_trained_inference(client):
    response = client.post(
        "/api/match",
        data={"gallery_mode": "uploaded"},
        files=[
            ("sketch", ("query.png", image_bytes(), "image/png")),
            ("gallery", ("person-one.png", image_bytes(), "image/png")),
            ("gallery", ("person-two.png", image_bytes(), "image/png")),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gallery_size"] == 2
    assert body["correct_rank"] is None
    assert [match["rank"] for match in body["matches"]] == [1, 2]
    assert all(-1 <= match["similarity"] <= 1 for match in body["matches"])
    assert body["matches"][0]["similarity"] >= body["matches"][1]["similarity"]
    assert body["matches"][0]["thumbnail"].startswith("data:image/jpeg;base64,")


@pytest.mark.skipif(not Path("runs/matcher/best.pt").exists(), reason="Requires real checkpoint")
def test_dataset_retrieval_matches_recorded_experiment(client):
    import json

    cases = json.loads(Path("outputs/results/matcher/retrievals.json").read_text())
    example = cases[0]
    response = client.post("/api/match", data={"example_id": example["query"]})
    assert response.status_code == 200
    body = response.json()
    assert body["correct_rank"] == example["correct_rank"]
    assert body["matches"][0]["candidate_id"] == example["top"][0]["identity"]
    assert len(body["matches"]) == 5
