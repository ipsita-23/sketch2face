# Sketch2Face paper source

This manuscript targets the exact [official IEEE Signal Processing Society conference and workshop template](https://www.overleaf.com/latex/templates/ieee-signal-processing-society-conference-and-workshop-template/xdqvgfmfghwj), using `\documentclass[cameraready]{ieeeconf}` at the class default 10 pt size. The template is for the paper. The separate 16-slide presentation is a college viva deck.

## Template acquisition status

The unmodified main template source was downloaded from the linked page's `modalViewSource` code block on 9 November 2026 and saved as `template/ieeeconf.tex`. Its header identifies **IEEE Conference Template v1.0 (2026/10/15)** and requires `ieeeconf.cls` v1.0. The page credits IEEE Signal Processing Society and lists LPPL 1.3c. The Overleaf template version is **53265**, with template identifier **283735593**.

The supporting `ieeeconf.cls` has **not yet been obtained**. The public gallery page exposes the main `.tex` only; opening the complete template redirects to Overleaf login. Tested public source archive routes returned 404. The ordinary IEEE download supplies `IEEEtran.cls`, which is a different class and has not been substituted. The class also differs from the older Control Systems Society class sharing the filename `ieeeconf.cls`.

**No PDF has yet been compiled with this SPS template.** The pre-existing `outputs/academic/research_paper.pdf` is the earlier manually formatted paper and must not be represented as the requested official-template build. The paper builder deliberately stops when the official class is missing.

## Compile in Overleaf

1. Open the official template link and choose **Open as Template** in an Overleaf account. Retain its supplied class and supporting files.
2. Upload this folder's `main.tex` and `figures/cmc_comparison.png` into that project.
3. Set `main.tex` as the main document and compile with pdfLaTeX. The author is visible because the manuscript uses `cameraready`.
4. To produce a self-contained local source package, download the official template ZIP and place its unmodified `ieeeconf.cls` and any supporting `.sty` files beside `main.tex`. Then run the builder below.

## Rebuild locally

From the repository root, use Python with python-docx installed and a TeX engine:

```bash
python scripts/build_paper_latex.py
```

The default engine is Tectonic. To use pdfLaTeX:

```bash
ACADEMIC_TEX_ENGINE=pdflatex python scripts/build_paper_latex.py
```

Once the actual class is present, the builder regenerates `main.tex` from the project narrative and saved experiment summary, compiles the PDF, and creates `outputs/academic/research_paper_overleaf.zip`. The ZIP includes sources and the numeric CMC plot, excluding build files, checkpoints and dataset faces. `template/ieeeconf.tex` retains the original template as a provenance reference. Select `main.tex` in Overleaf.

## Evidence and interpretation

`outputs/results/summary.json` establishes 188 verified CUHK pairs, split 114/37/37, with 37 held-out sketch queries searching a fixed 37-photo gallery. The primary run achieves 72.97% rank-1, 89.19% rank-5 and 100% observed rank-10. Frozen baseline rank-1 is 27.03%; the three-seed matcher mean is 69.37%, with sample standard deviation 3.12 percentage points. The adapter ablation has mixed effects. These results do not establish full 606-identity CUFS performance, open-set rejection or forensic validity.

The paper names Ipsita and Lovely Professional University. The viva deck retains B.Tech AI and ML, 2023–2027, roll `12308012 (placeholder)`, and the guide placeholder. The college submission fields are not invented research coauthors.
