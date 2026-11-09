"""Build the paper with the unmodified official IEEE SPS class; never emulate it."""

import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from build_academic import REFERENCES, TITLE, content, metrics_table

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "academic/latex"
OUT = ROOT / "outputs/academic"


def tex(value):
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    value = "".join(replacements.get(c, c) for c in str(value))
    value = value.replace("±", r"$\pm$").replace("–", "--").replace("—", "---")
    return re.sub(r"\[(\d+)\]", lambda m: r"\cite{ref" + m[1] + "}", value)


def generate():
    summary = json.loads((ROOT / "outputs/results/summary.json").read_text())
    abstract, sections = content(summary)
    SOURCE.mkdir(parents=True, exist_ok=True)
    (SOURCE / "figures").mkdir(exist_ok=True)
    shutil.copyfile(
        ROOT / "outputs/figures/cmc_comparison.png", SOURCE / "figures/cmc_comparison.png"
    )
    lines = [
        r"\documentclass[cameraready]{ieeeconf}",
        r"\usepackage{booktabs}",
        r"\usepackage{graphicx}",
        r"\usepackage{amsmath}",
        r"\title{" + tex(TITLE) + "}",
        r"\addauthor{Ipsita}{1}",
        r"\addaffiliation{1}{B.Tech in Artificial Intelligence and Machine Learning, Lovely Professional University, Punjab, India}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{abstract}",
        tex(abstract),
        r"\end{abstract}",
    ]
    for i, (title, paragraphs) in enumerate(sections):
        lines.append(r"\section{" + tex(title.split(" ", 1)[1]) + "}")
        lines.extend(tex(p) + "\n" for p in paragraphs)
        if i == 3:
            lines.extend(
                [
                    r"\begin{equation}",
                    r"\mathcal{L}=\tfrac{1}{2}\left[\mathrm{CE}(Z_s Z_p^\top/\tau,y)+\mathrm{CE}(Z_p Z_s^\top/\tau,y)\right],",
                    r"\end{equation}",
                    r"where $y_i=i$, $\tau=0.07$, and rows of $Z_s$ and $Z_p$ are normalized embeddings.",
                ]
            )
        if i == 5:
            rows = metrics_table(summary)
            lines.extend(
                [
                    r"\begin{table}[t]",
                    r"\centering",
                    r"\caption{Retrieval accuracy (\%) on 37 test queries and the same 37-photo gallery. Epoch selection uses validation only.}",
                    r"\label{tab:results}",
                    r"\small",
                    r"\begin{tabular}{lrrrr}",
                    r"\toprule",
                    r"Model & Epoch & R@1 & R@5 & R@10 \\",
                    r"\midrule",
                ]
            )
            lines.extend(" & ".join(tex(c) for c in row) + r" \\" for row in rows[1:])
            lines.extend(
                [
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\end{table}",
                    r"\begin{figure}[t]",
                    r"\centering",
                    r"\includegraphics[width=\linewidth]{figures/cmc_comparison.png}",
                    r"\caption{Measured CMC under the fixed 37-photo test protocol. This figure contains no dataset face images.}",
                    r"\label{fig:cmc}",
                    r"\end{figure}",
                ]
            )
    lines.append(r"\begin{thebibliography}{6}")
    for i, ref in enumerate(REFERENCES, 1):
        # Plain URLs are typeset with url's line-break support supplied by the class.
        ref = re.sub(r"^\[\d+\] ", "", ref)
        chunks = re.split(r"(https?://\S+)", ref)
        rendered = "".join(
            r"\url{" + v.rstrip(".") + "}" + ("." if v.endswith(".") else "")
            if v.startswith("http")
            else tex(v)
            for v in chunks
        )
        lines.append(r"\bibitem{ref" + str(i) + "} " + rendered)
    lines.extend([r"\end{thebibliography}", r"\end{document}"])
    (SOURCE / "main.tex").write_text("\n\n".join(lines) + "\n")


def build():
    generate()
    cls = SOURCE / "ieeeconf.cls"
    if not cls.exists():
        raise SystemExit(
            "Official IEEE SPS ieeeconf.cls is required in academic/latex/. No substitute class will be used."
        )
    text = cls.read_text()
    if "cameraready" not in text or "addauthor" not in text:
        raise SystemExit("This is not the requested SPS class: cameraready/addauthor are missing.")
    stage = ROOT / "tmp/academic/latex-build"
    stage.mkdir(parents=True, exist_ok=True)
    engine = os.environ.get("ACADEMIC_TEX_ENGINE", "tectonic")
    if Path(engine).name == "tectonic":
        cmd = [
            engine,
            "--keep-logs",
            "--keep-intermediates",
            "--outdir",
            str(stage),
            str(SOURCE / "main.tex"),
        ]
        subprocess.run(cmd, cwd=SOURCE, check=True)
    else:
        cmd = [
            engine,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "-output-directory=" + str(stage),
            "main.tex",
        ]
        for _ in range(2):
            subprocess.run(cmd, cwd=SOURCE, check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stage / "main.pdf", OUT / "research_paper.pdf")
    # Package sources only: no dataset images, local paths, checkpoints or build residue.
    with zipfile.ZipFile(OUT / "research_paper_overleaf.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SOURCE.rglob("*")):
            if p.is_file() and p.suffix in {
                ".tex",
                ".cls",
                ".sty",
                ".bst",
                ".bib",
                ".png",
                ".md",
                ".json",
                ".txt",
            }:
                z.write(p, p.relative_to(SOURCE))
    print("Official-class PDF and Overleaf source ZIP written to", OUT)


def prepare_overlay():
    generate()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "research_paper_template_overlay.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SOURCE.rglob("*")):
            if path.is_file() and path.suffix in {".tex", ".png", ".md", ".json"}:
                archive.write(path, path.relative_to(SOURCE))
    print("Template overlay only; import into the official Overleaf template project:", target)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare-overlay",
        action="store_true",
        help="Prepare source for upload into an existing official Overleaf template project; does not compile or include the missing class",
    )
    args = parser.parse_args()
    if args.prepare_overlay:
        prepare_overlay()
    else:
        build()
