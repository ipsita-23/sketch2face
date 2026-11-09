"""Local Streamlit demo: `.venv/bin/streamlit run app.py`."""

import json
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from sketch2face.data import load_manifest, open_image
from sketch2face.engine import choose_device, rank_images
from sketch2face.model import load_checkpoint

st.set_page_config(page_title="Sketch2Face", page_icon="✏️", layout="wide")
st.title("Sketch2Face")
st.write(
    "Find the closest face photos to a sketch. Upload your own images or try held-out CUHK examples."
)
st.caption(
    "College research prototype · viewed artist sketches · similarity scores are not identity probabilities"
)

checkpoints = sorted(Path("runs").glob("*/best.pt"))
if not checkpoints:
    st.info("No checkpoint found. Follow README.md to download the dataset and train the model.")
    st.stop()
preferred = next((i for i, path in enumerate(checkpoints) if path.parent.name == "matcher"), 0)
checkpoint = st.sidebar.selectbox("Model checkpoint", checkpoints, index=preferred, format_func=str)
st.sidebar.write("Use aligned face crops with similar framing to the training images.")
mode = st.sidebar.radio("Input", ["Dataset examples", "Upload images"])
device = choose_device()


@st.cache_resource
def get_model(path, modified):
    return load_checkpoint(path, choose_device())


model, payload = get_model(str(checkpoint), checkpoint.stat().st_mtime_ns)
st.sidebar.caption(f"Device: {device} · Selected epoch: {payload['epoch']}")
st.sidebar.caption(payload["dataset"])
sketch, photos, names, correct = None, [], [], None
try:
    if mode == "Dataset examples":
        if not Path("data/manifest.json").exists():
            st.info("Dataset examples require data/manifest.json.")
            st.stop()
        manifest = load_manifest("data/manifest.json")
        if manifest["fingerprint"] != payload["manifest_fingerprint"]:
            st.error("This checkpoint was trained using a different dataset manifest.")
            st.stop()
        rows = [row for row in manifest["rows"] if row["split"] == "test"]
        selection = st.selectbox(
            "Held-out sketch", range(len(rows)), format_func=lambda i: rows[i]["uid"]
        )
        sketch = open_image(rows[selection]["sketch"])
        photos = [open_image(row["photo"]) for row in rows]
        names = [row["uid"] for row in rows]
        correct = rows[selection]["uid"]
        st.caption(
            f"Gallery: all {len(rows)} held-out photos. These identities were excluded from training and validation."
        )
    else:
        query = st.file_uploader("Sketch", type=["jpg", "jpeg", "png", "bmp"])
        gallery = st.file_uploader(
            "Candidate photos", type=["jpg", "jpeg", "png", "bmp"], accept_multiple_files=True
        )
        if len(gallery) > 200:
            st.error(
                "Limit each interactive gallery to 200 photos. Use the CLI for larger galleries."
            )
            st.stop()
        if query:
            sketch = ImageOps.exif_transpose(Image.open(query)).convert("RGB")
        for upload in gallery:
            photos.append(ImageOps.exif_transpose(Image.open(upload)).convert("RGB"))
            names.append(upload.name)
    if sketch is not None:
        st.image(sketch, caption="Query sketch", width=180)
    if sketch is not None and photos and st.button("Find matching photos", type="primary"):
        with st.spinner("Comparing facial features…"):
            ranking = rank_images(model, sketch, photos, device, size=payload["config"]["size"])
        if correct:
            position = next(i + 1 for i, (j, _) in enumerate(ranking) if names[j] == correct)
            st.info(f"Correct photo appears at rank {position} of {len(photos)}.")
        for start in range(0, min(10, len(ranking)), 5):
            columns = st.columns(5)
            for offset, (j, score) in enumerate(ranking[start : start + 5]):
                with columns[offset]:
                    label = f"#{start + offset + 1} · {names[j]}"
                    if names[j] == correct:
                        label += " ✓ correct"
                    st.image(photos[j], caption=label, width="stretch")
                    st.caption(f"Cosine similarity: {score:.4f}")
        results = [
            {"rank": i + 1, "photo": names[j], "similarity": score}
            for i, (j, score) in enumerate(ranking)
        ]
        st.download_button(
            "Download ranking (JSON)",
            json.dumps(results, indent=2),
            "matches.json",
            "application/json",
        )
except (OSError, ValueError, UnidentifiedImageError) as error:
    st.error(str(error))
