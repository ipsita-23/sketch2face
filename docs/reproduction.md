# Reproduction and submission guide

## Environment and commands

Use Python 3.11–3.13. `uv.lock` pins dependencies. Device selection prefers CUDA, Apple MPS, then CPU. No paid API key is needed. Network access is required for the mirror and official torchvision weights on first use. Allow at least 2 GB free for dependencies, images, checkpoints, and artifacts.

```bash
uv sync --extra dev --extra documents
uv run python scripts/download_cufs.py
uv run python scripts/run_experiments.py
uv run python scripts/make_figures.py
uv run python scripts/build_academic.py
uv run pytest -q
uv run streamlit run app.py
```

The downloader rejects a changed mirror layout instead of guessing pairings. To inspect results, open `outputs/results/summary.json` and the Markdown academic sources.

## Rendering Office documents

The academic builder creates report DOCX, paper DOCX/PDF, presentation PPTX, and Markdown sources. Office PDF export needs LibreOffice. Standard local commands:

```bash
soffice --headless --convert-to pdf --outdir outputs/academic outputs/academic/project_report.docx
soffice --headless --convert-to pdf --outdir outputs/academic outputs/academic/research_paper.docx
soffice --headless --convert-to pdf --outdir outputs/academic outputs/academic/presentation.pptx
```

The delivered artifacts are rendered and checked using the bundled artifact runtime. The paper uses an A4, two-column IEEE-style layout, not a claim of compliance with an official conference template. Word and LibreOffice line breaks may differ; use the PDF for stable reading. Verify departmental guidelines: Indian institutions do not share one universal paper template.

## Cover details

Lovely Professional University; B.Tech in Artificial Intelligence and Machine Learning; Ipsita; academic period 2023–2027. Roll number 12308012 is explicitly a placeholder; guide name is also a placeholder. Replace these in `scripts/build_academic.py` and rerun, or edit Office files. No signatures, approval certificate, official logo, or university endorsement have been fabricated.

## New training runs

```bash
uv run sketch2face train --output runs/reproduction_seed42 --seed 42 --epochs 20
uv run sketch2face evaluate --checkpoint runs/reproduction_seed42/best.pt --output runs/reproduction_seed42/test
```

Do not tune on test numbers. State a validation-driven selection policy before any new test evaluation. Different data needs a separate manifest and run directory. Existing evidence directories are protected from accidental overwriting.

## Troubleshooting

| Problem | Action |
|---|---|
| Python 3.14/3.15 errors | Use `uv python install 3.11`, then `uv sync --python 3.11` |
| Official CUHK page unavailable | Use recorded mirror downloader; retain the subset scope |
| Weights download fails | Restore network or official torch cache; random weights change the experiment |
| MPS/CUDA unavailable | Pass `--device cpu` |
| Manifest hash mismatch | Restore images; changed data needs a new manifest and training |
| Existing run directory | Choose a new directory |
| Poor uploaded-image matching | Check framing and sketch style; similarities are not probabilities |
| Guide/roll number incomplete | Replace marked placeholders before submission |
