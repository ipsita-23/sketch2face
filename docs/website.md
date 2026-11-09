# Sketch2Face website

Start the local website from the project root:

```bash
uv sync --extra dev
uv run uvicorn sketch2face.web:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Upload a cropped face sketch, then search the built-in held-out gallery or upload your own candidate photographs. The sample-sketch button lets you try a real held-out example immediately. The output is a ranked shortlist with cosine similarities; it cannot find a person whose photo is absent, provide their real name, or establish their identity. Uploaded photo filenames are used as candidate labels.

The website uses the trained checkpoint at `runs/matcher/best.pt`. Override with `SKETCH2FACE_CHECKPOINT`; paths are resolved relative to the project root. Dataset examples require `data/manifest.json` and its matching checkpoint fingerprint. Custom gallery retrieval works without the dataset manifest. If weights are unavailable, the page still loads and explains how to train; the API returns 503 for inference.

Uploads are not retained after the request. The multipart parser may use temporary files for larger uploads and cleans them up after processing; the application does not create a persistent upload gallery. Supported formats are JPEG, PNG, and BMP; each file is limited to 8 MB, total uploaded image bytes to 32 MB, decoded images to 20 million pixels, and a custom gallery to 200 photos. Candidate images are resized for memory use. The server binds only to localhost in the documented command; it has no authentication or public hosting configuration.

## HTTP contract

The machine-readable OpenAPI contract is served at `/openapi.json`; interactive documentation is at `/docs`.

| Endpoint | Behavior |
|---|---|
| `GET /api/status` | Model readiness, dataset gallery size, accepted formats and limits |
| `GET /api/examples` | Available held-out sketch/photo IDs and image URLs; no arbitrary filesystem paths |
| `GET /api/images/{identity}/{modality}` | Thumbnail of an allowlisted test image; modality is sketch or photo |
| `POST /api/match` | Multipart sketch/gallery retrieval; returns up to 10 ranked photo thumbnails and cosine scores |

`POST /api/match` accepts `sketch` (one file) or `example_id` (one held-out ID), exactly one of these. `gallery_mode` is `dataset` or `uploaded`; the latter requires repeated `gallery` file fields. Optional `top_k` is an integer from 1 through 10, default 5. Dataset mode uses every held-out photo from the checkpoint-matched manifest. A request mixing gallery files with dataset mode is rejected.

The response contains `matches` (rank, candidate ID, filename label, similarity, thumbnail data URL), `gallery_size`, `elapsed_ms`, and `gallery_mode`. Dataset examples additionally return `correct_rank`; that is evaluation ground truth, never an inferred real-world identity. Similarity is a raw cosine value in [-1,1], not a percentage confidence. Errors have a human-readable `detail`: 422 for invalid combinations or images, 413 for upload limits, 404 for unknown example IDs, and 503 for missing model/data. The server computes actual embeddings and never fabricates results.

## Verification

The API integration tests exercise uploaded sketch and photo bytes with a real checkpoint, malformed/oversized images, missing and mixed input modes, missing weights, dataset matching, thumbnail allowlisting, and score order. The UI is additionally checked in the shared browser. No external inference API is called; inference runs locally in PyTorch.
