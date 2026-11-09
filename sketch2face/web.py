"""Local website and upload API. Run: uvicorn sketch2face.web:app --port 8000."""

import base64
import io
import os
import threading
import time
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from .data import load_manifest, open_image
from .engine import choose_device, rank_images
from .model import load_checkpoint

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / os.environ.get("SKETCH2FACE_CHECKPOINT", "runs/matcher/best.pt")
MANIFEST = ROOT / "data/manifest.json"
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_PIXELS = 20_000_000
INFERENCE_LOCK = threading.Lock()

app = FastAPI(
    title="Sketch2Face website API",
    version="1.0.0",
    description="Local cross-modal sketch-to-photo retrieval. Similarities are not identity probabilities.",
)
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


class Match(BaseModel):
    rank: int
    candidate_id: str
    label: str
    similarity: float
    thumbnail: str


class MatchResponse(BaseModel):
    matches: list[Match]
    gallery_size: int
    gallery_mode: Literal["dataset", "uploaded"]
    elapsed_ms: int
    correct_rank: int | None = None


@lru_cache(maxsize=1)
def trained_model():
    if not CHECKPOINT.is_file():
        raise HTTPException(
            503,
            "The trained model is missing. Download the dataset and run scripts/run_experiments.py first.",
        )
    device = choose_device()
    model, payload = load_checkpoint(CHECKPOINT, device)
    return model, payload, device


@lru_cache(maxsize=1)
def dataset():
    try:
        manifest = load_manifest(MANIFEST)
        rows = [row for row in manifest["rows"] if row["split"] == "test"]
        if not rows:
            raise ValueError("No held-out examples in the manifest.")
        return manifest, rows
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(
            503,
            "The built-in gallery is unavailable. Download and prepare CUFS, or upload your own gallery.",
        ) from error


def jpeg_bytes(image, size=320):
    preview = image.copy()
    preview.thumbnail((size, size))
    output = io.BytesIO()
    preview.save(output, format="JPEG", quality=88)
    return output.getvalue()


def image_data_url(image):
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes(image)).decode("ascii")


def decode_upload(file):
    raw = file.file.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise HTTPException(413, "Each image must be 8 MB or smaller.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in {"JPEG", "PNG", "BMP"}:
                    raise HTTPException(422, "Please upload JPEG, PNG, or BMP images.")
                if min(source.size) < 32 or source.width * source.height > MAX_PIXELS:
                    raise HTTPException(
                        422,
                        "Images must be at least 32 pixels on each side and no more than 20 megapixels.",
                    )
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1600, 1600))
                return image, len(raw)
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise HTTPException(
            422,
            "One of the files is not a readable image. Please choose a valid JPEG, PNG, or BMP.",
        ) from error


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "web/index.html")


@app.get("/api/status")
def status():
    try:
        _, rows = dataset()
        gallery_size = len(rows)
    except HTTPException:
        gallery_size = 0
    return {
        "model_ready": CHECKPOINT.is_file(),
        "gallery_size": gallery_size,
        "formats": ["JPEG", "PNG", "BMP"],
        "max_file_mb": 8,
        "max_total_mb": 32,
        "max_gallery": 200,
        "dataset_scope": "CUFS CUHK subset",
    }


@app.get("/api/examples")
def examples():
    _, rows = dataset()
    return {
        "examples": [
            {
                "id": row["uid"],
                "sketch_url": f"/api/images/{row['uid']}/sketch",
                "photo_url": f"/api/images/{row['uid']}/photo",
            }
            for row in rows
        ]
    }


@app.get(
    "/api/images/{identity}/{modality}", responses={404: {"description": "Unknown test image"}}
)
def example_image(identity: str, modality: Literal["sketch", "photo"]):
    _, rows = dataset()
    row = next((row for row in rows if row["uid"] == identity), None)
    if row is None:
        raise HTTPException(404, "Example not found.")
    return Response(
        jpeg_bytes(open_image(row[modality])),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


@app.post(
    "/api/match",
    response_model=MatchResponse,
    responses={
        413: {"description": "Image upload limits exceeded"},
        422: {"description": "Invalid images or input combination"},
        503: {"description": "Model or dataset unavailable"},
    },
)
def match(
    sketch: Annotated[UploadFile | None, File()] = None,
    example_id: Annotated[str | None, Form()] = None,
    gallery_mode: Annotated[Literal["dataset", "uploaded"], Form()] = "dataset",
    gallery: Annotated[list[UploadFile] | None, File()] = None,
    top_k: Annotated[int, Form(ge=1, le=10)] = 5,
):
    gallery = gallery or []
    if bool(sketch) == bool(example_id):
        raise HTTPException(422, "Upload a sketch or choose one sample sketch, but not both.")
    if gallery_mode == "dataset" and gallery:
        raise HTTPException(422, "Choose your own photo gallery to use uploaded candidate photos.")
    if gallery_mode == "uploaded" and not gallery:
        raise HTTPException(422, "Upload at least one candidate photo.")
    if len(gallery) > 200:
        raise HTTPException(413, "A gallery can contain at most 200 photos.")
    started = time.monotonic()
    total = 0
    truth = None
    if sketch:
        query, total = decode_upload(sketch)
    else:
        _, rows = dataset()
        row = next((row for row in rows if row["uid"] == example_id), None)
        if row is None:
            raise HTTPException(404, "Sample sketch not found.")
        query = open_image(row["sketch"])
        truth = example_id
    photos, names, ids = [], [], []
    if gallery_mode == "dataset":
        manifest, rows = dataset()
        photos = [open_image(row["photo"]) for row in rows]
        names = [row["uid"] for row in rows]
        ids = names.copy()
    else:
        for i, file in enumerate(gallery):
            image, count = decode_upload(file)
            total += count
            if total > MAX_TOTAL:
                raise HTTPException(413, "Combined image uploads must be 32 MB or smaller.")
            photos.append(image)
            names.append(
                (file.filename or f"Photo {i + 1}").replace("\\", "/").split("/")[-1][:120]
            )
            ids.append(f"upload-{i}")
    with INFERENCE_LOCK:
        model, payload, device = trained_model()
        if gallery_mode == "dataset" and payload["manifest_fingerprint"] != manifest["fingerprint"]:
            raise HTTPException(
                503,
                "The built-in gallery does not match this model. Upload your own candidate photos instead.",
            )
        ranking = rank_images(model, query, photos, device, size=payload["config"]["size"])
    result = {
        "matches": [
            {
                "rank": i + 1,
                "candidate_id": ids[j],
                "label": names[j],
                "similarity": round(min(1.0, max(-1.0, score)), 6),
                "thumbnail": image_data_url(photos[j]),
            }
            for i, (j, score) in enumerate(ranking[:top_k])
        ],
        "gallery_size": len(photos),
        "gallery_mode": gallery_mode,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "correct_rank": None,
    }
    if truth and gallery_mode == "dataset":
        result["correct_rank"] = next(i + 1 for i, (j, _) in enumerate(ranking) if ids[j] == truth)
    return result
