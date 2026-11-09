"use strict";
const $ = (id) => document.getElementById(id);
let statusInfo = null,
  samples = [],
  sampleIndex = -1,
  queryFile = null,
  sampleId = null;
let galleryFiles = [],
  previewUrl = null,
  galleryUrls = [],
  currentResults = null,
  busy = false;
const showError = (message) => {
  $("error-message").textContent = message;
  $("error-message").hidden = !message;
};
const mode = () =>
  document.querySelector('input[name="gallery-mode"]:checked').value;
const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
function updateButton() {
  $("match-button").disabled =
    busy ||
    !statusInfo?.model_ready ||
    !(queryFile || sampleId) ||
    (mode() === "uploaded" ? !galleryFiles.length : !statusInfo.gallery_size);
}
function clearResults() {
  currentResults = null;
  $("populated-results").hidden = true;
  $("empty-results").hidden = false;
  $("results-count").textContent = "AWAITING YOUR SKETCH";
  showError("");
}
function setPreview(url, label) {
  $("sketch-empty").hidden = true;
  $("sketch-preview").hidden = false;
  $("sketch-preview").src = url;
  $("sketch-preview").alt = label;
  document.querySelector(".replace-hint").hidden = false;
  $("query-label").hidden = false;
  $("query-label").textContent = label;
  clearResults();
  updateButton();
}
function checkFile(file) {
  if (file.size > 8 * 1024 * 1024)
    throw new Error("Each image must be 8 MB or smaller.");
  if (!/\.(jpe?g|png|bmp)$/i.test(file.name))
    throw new Error("Please choose a JPG, PNG, or BMP image.");
}
function chooseSketch(file) {
  if (!file || busy) return;
  try {
    checkFile(file);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    queryFile = file;
    sampleId = null;
    setPreview(previewUrl, file.name);
  } catch (error) {
    showError(error.message);
    $("sketch-file").value = "";
  }
}
async function api(url, options) {
  const response = await fetch(url, options);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The matcher is unavailable. Please try again.");
  }
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(". ")
      : data.detail;
    throw new Error(
      detail || "The search could not complete. Please try again.",
    );
  }
  return data;
}
async function initialise() {
  try {
    statusInfo = await api("/api/status");
    $("model-status").className =
      "status " + (statusInfo.model_ready ? "ready" : "unavailable");
    $("model-status").replaceChildren(
      el("span"),
      document.createTextNode(
        statusInfo.model_ready
          ? "Model ready · local inference"
          : "Trained model unavailable",
      ),
    );
    if (!statusInfo.model_ready)
      showError(
        "The trained model is not available yet. Follow the setup steps in README.md to enable matching.",
      );
    $("gallery-description").textContent =
      `${statusInfo.gallery_size} held-out CUHK face photos`;
    if (statusInfo.gallery_size) {
      const data = await api("/api/examples");
      samples = data.examples;
      for (const sample of samples.slice(0, 5)) {
        const image = el("img");
        image.src = sample.photo_url;
        image.alt = "Candidate " + sample.id;
        $("gallery-preview").append(image);
      }
      $("gallery-preview").append(
        el("span", "", `+${Math.max(0, samples.length - 5)} photos to search`),
      );
    } else {
      $("sample-button").disabled = true;
      document.querySelector('input[value="dataset"]').disabled = true;
      document.querySelector('input[value="uploaded"]').checked = true;
      $("custom-gallery").hidden = false;
      $("gallery-preview").hidden = true;
    }
    updateButton();
  } catch (error) {
    $("model-status").textContent = "Connection unavailable";
    showError(error.message);
  }
}
$("sketch-file").addEventListener("change", (event) =>
  chooseSketch(event.target.files[0]),
);
$("sketch-drop").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    if (!busy) $("sketch-file").click();
  }
});
for (const name of ["dragenter", "dragover"])
  $("sketch-drop").addEventListener(name, (event) => {
    event.preventDefault();
    if (!busy) $("sketch-drop").classList.add("dragging");
  });
for (const name of ["dragleave", "drop"])
  $("sketch-drop").addEventListener(name, (event) => {
    event.preventDefault();
    $("sketch-drop").classList.remove("dragging");
    if (name === "drop") chooseSketch(event.dataTransfer.files[0]);
  });
$("sample-button").addEventListener("click", () => {
  if (!samples.length || busy) return;
  sampleIndex = (sampleIndex + 1) % samples.length;
  const sample = samples[sampleIndex];
  queryFile = null;
  sampleId = sample.id;
  $("sketch-file").value = "";
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }
  setPreview(sample.sketch_url, `Sample sketch · ${sample.id}`);
});
document.querySelectorAll('input[name="gallery-mode"]').forEach((input) =>
  input.addEventListener("change", () => {
    $("custom-gallery").hidden = mode() !== "uploaded";
    $("gallery-preview").hidden = mode() !== "dataset";
    clearResults();
    updateButton();
  }),
);
$("gallery-files").addEventListener("change", (event) => {
  const files = Array.from(event.target.files);
  try {
    if (files.length > 200)
      throw new Error("Please choose no more than 200 candidate photos.");
    files.forEach(checkFile);
    if (
      files.reduce((sum, file) => sum + file.size, queryFile?.size || 0) >
      32 * 1024 * 1024
    )
      throw new Error("Combined uploads must be 32 MB or smaller.");
    galleryFiles = files;
    galleryUrls.forEach((url) => URL.revokeObjectURL(url));
    galleryUrls = [];
    $("custom-thumbnails").replaceChildren();
    for (const file of files.slice(0, 12)) {
      const url = URL.createObjectURL(file);
      galleryUrls.push(url);
      const img = el("img");
      img.src = url;
      img.alt = file.name;
      $("custom-thumbnails").append(img);
    }
    $("gallery-count").textContent = files.length
      ? `${files.length} candidate photo${files.length === 1 ? "" : "s"} selected`
      : "Up to 200 photos · 32 MB total";
    clearResults();
    updateButton();
  } catch (error) {
    showError(error.message);
    event.target.value = "";
    galleryFiles = [];
    $("custom-thumbnails").replaceChildren();
    $("gallery-count").textContent = "No candidate photos selected";
    updateButton();
  }
});
function renderResults(data) {
  currentResults = data;
  $("empty-results").hidden = true;
  $("populated-results").hidden = false;
  $("results-count").textContent =
    `${data.matches.length} CLOSEST MATCH${data.matches.length === 1 ? "" : "ES"}`;
  $("best-match").replaceChildren();
  $("other-matches").replaceChildren();
  const first = data.matches[0];
  const card = el("article", "best-card"),
    image = el("img", "best-photo");
  image.src = first.thumbnail;
  image.alt = `Top candidate: ${first.label}`;
  const info = el("div", "best-info");
  info.append(
    el("span", "best-tag", "01 / TOP CANDIDATE"),
    el("h3", "", first.label),
    el("span", "similarity-label", "Cosine similarity"),
    el("span", "similarity-value", first.similarity.toFixed(4)),
    el(
      "p",
      "",
      "The closest match in this gallery. Review the alternatives below.",
    ),
  );
  card.append(image, info);
  $("best-match").append(card);
  for (const match of data.matches.slice(1)) {
    const item = el("article", "candidate-card"),
      photo = el("img");
    photo.src = match.thumbnail;
    photo.alt = `Candidate ${match.rank}: ${match.label}`;
    item.append(
      photo,
      el("span", "candidate-rank", String(match.rank).padStart(2, "0")),
      el("h4", "", match.label),
      el("p", "", match.similarity.toFixed(4) + " similarity"),
    );
    $("other-matches").append(item);
  }
  document.querySelector(".runner-heading").hidden = data.matches.length < 2;
  $("demo-ground-truth").hidden = data.correct_rank === null;
  $("demo-ground-truth").textContent =
    `Sample check: the correct photo appears at rank ${data.correct_rank} of ${data.gallery_size}.`;
  $("search-meta").textContent =
    `${data.gallery_size} photo${data.gallery_size === 1 ? "" : "s"} compared · ${(data.elapsed_ms / 1000).toFixed(2)} s`;
}
function setBusy(value) {
  busy = value;
  $("results-panel").setAttribute("aria-busy", String(value));
  $("loading-results").hidden = !value;
  document
    .querySelectorAll("input, #sample-button")
    .forEach((input) => (input.disabled = value));
  if (!value) {
    $("sample-button").disabled = !samples.length;
    document.querySelector('input[value="dataset"]').disabled =
      !statusInfo?.gallery_size;
  }
  $("match-button").querySelector("span").textContent = value
    ? "Comparing faces…"
    : "Find matching faces";
  updateButton();
}
$("match-button").addEventListener("click", async () => {
  if (busy) return;
  const form = new FormData();
  if (queryFile) form.append("sketch", queryFile);
  else form.append("example_id", sampleId);
  form.append("gallery_mode", mode());
  form.append("top_k", "5");
  if (mode() === "uploaded")
    galleryFiles.forEach((file) => form.append("gallery", file));
  clearResults();
  $("empty-results").hidden = true;
  setBusy(true);
  try {
    renderResults(await api("/api/match", { method: "POST", body: form }));
  } catch (error) {
    $("empty-results").hidden = false;
    showError(error.message);
  } finally {
    setBusy(false);
  }
});
$("download-results").addEventListener("click", () => {
  if (!currentResults) return;
  const data = {
    ...currentResults,
    matches: currentResults.matches.map(({ thumbnail, ...match }) => match),
  };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const link = el("a");
  link.href = url;
  link.download = "sketch2face-matches.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
initialise();
