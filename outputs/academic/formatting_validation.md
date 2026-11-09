# Academic formatting validation

Validated on 9 November 2026 against `outputs/results/summary.json`.

## Viva presentation

The updated presentation has 16 slides, two native editable tables, two native editable charts and 16 speaker-note parts. Structural package checks, slide geometry, heading fit, Arial font policy, chart-to-workbook relationships and a fresh Artifact Tool import passed with zero findings. The chart workbooks are snapshots of numeric values from the saved summary, rounded to six decimal places in percentage units for Excel compatibility. Display tables retain two decimal places.

The bundled JavaScript runtime authored the PPTX. The bundled headless LibreOffice runtime produced its 16-page PDF. Slides were rendered for visual review. This is not a claim that the files were opened in Microsoft PowerPoint.

The primary result, repeated seeds, frozen baseline and no-adapter ablation agree with the saved evidence. CMC uses unsmoothed connections between measured ranks. The deck includes no dataset face images. The notes distinguish viewed sketches, the fixed 37-photo closed-set gallery, and the mixed ablation result from forensic validation. Slide 15 and its notes describe the verified FastAPI website upload workflow; Streamlit remains an optional legacy interface. Student roll and guide placeholders remain explicitly marked.

## Paper template

The official Overleaf page's unmodified template main source is preserved at `academic/latex/template/ieeeconf.tex`, with acquisition metadata and SHA-256 in `academic/latex/template/provenance.json`. The source header is IEEE Conference Template v1.0 dated 2026/10/15. `academic/latex/main.tex` uses `\documentclass[cameraready]{ieeeconf}` and the template's `\addauthor` and `\addaffiliation` commands.

The actual supporting SPS class has not yet been obtained. Therefore no exact-template compilation, page-layout validation, font embedding validation or self-contained Overleaf ZIP is claimed. The builder's missing-class check was exercised and stopped as intended. The earlier `research_paper.pdf` remains the earlier manually formatted artifact. It is not the requested exact-template PDF.

`research_paper_template_overlay.zip` contains the manuscript, CMC plot and provenance. It is for upload into a project created from the official Overleaf template, which supplies the missing class. It is not a self-contained replacement for that template. Python syntax compilation passed for both academic Python builders.
