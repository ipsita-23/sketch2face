"""Build the LPU report, IEEE-style paper and editable viva presentation from real metrics.

Run after run_experiments.py and make_figures.py. No dataset photos are embedded in
public academic artifacts; examples remain available locally through the app.
"""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor as PptColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches as PI
from pptx.util import Pt as PP
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/academic"
FIG = ROOT / "outputs/figures"
TITLE = "Sketch2Face Cross Modal Face Retrieval on the CUFS CUHK Subset"
STUDENT = "Ipsita"
UNIVERSITY = "Lovely Professional University"
PROGRAMME = "B.Tech in Artificial Intelligence and Machine Learning"
ROLL = "12308012 (placeholder)"
GUIDE = "[Guide name - placeholder]"
YEARS = "2023-2027"
REFERENCES = [
    '[1] X. Wang and X. Tang, "Face Photo-Sketch Synthesis and Recognition," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 31, no. 11, pp. 1955-1967, 2009. doi:10.1109/TPAMI.2008.222.',
    '[2] W. Zhang, X. Wang, and X. Tang, "Coupled Information-Theoretic Encoding for Face Photo-Sketch Recognition," IEEE CVPR, pp. 513-520, 2011.',
    '[3] K. He, X. Zhang, S. Ren, and J. Sun, "Deep Residual Learning for Image Recognition," IEEE CVPR, pp. 770-778, 2016. https://arxiv.org/abs/1512.03385.',
    '[4] A. Radford et al., "Learning Transferable Visual Models From Natural Language Supervision," ICML, PMLR 139, pp. 8748-8763, 2021. https://arxiv.org/abs/2103.00020.',
    '[5] I. Loshchilov and F. Hutter, "Decoupled Weight Decay Regularization," ICLR, 2019. https://arxiv.org/abs/1711.05101.',
    '[6] Arbaz Khan, "CUHK Face Sketch Database (CUFS)," Kaggle public mirror, version 1, updated October 8, 2020; accessed November 9, 2026. https://www.kaggle.com/datasets/arbazkhan971/cuhk-face-sketch-database-cufs. Data rights retained by original authors.',
]


def pct(value):
    return f"{value * 100:.2f}"


def metrics_table(summary):
    labels = [
        ("baseline", "Frozen baseline"),
        ("matcher", "Matcher seed 42"),
        ("matcher_seed43", "Matcher seed 43"),
        ("matcher_seed44", "Matcher seed 44"),
        ("shared_input", "Without adapters"),
    ]
    table = [["Model", "Epoch", "R1 (%)", "R5 (%)", "R10 (%)"]]
    for name, label in labels:
        run = summary["runs"][name]
        table.append(
            [label, str(run["selected_epoch"])]
            + [pct(run["overall"]["metrics"][f"rank_{k}"]["accuracy"]) for k in (1, 5, 10)]
        )
    return table


def content(summary):
    run = summary["runs"]["matcher"]
    primary = run["overall"]["metrics"]
    baseline = summary["runs"]["baseline"]["overall"]["metrics"]
    delta = summary["paired_rank1_difference"]
    seeds = summary["three_seed_summary"]
    r1, r5, r10 = [pct(primary[f"rank_{k}"]["accuracy"]) for k in (1, 5, 10)]
    b1 = pct(baseline["rank_1"]["accuracy"])
    low, high = primary["rank_1"]["ci95"]
    abstract = (
        "Matching a hand-drawn face sketch to a photographic gallery is difficult because identity must be preserved across different image domains. "
        "This project implements a cross-modal retrieval system using modality-specific residual input adapters, a shared ImageNet-pretrained ResNet-18, "
        "and a normalized 256-dimensional projection trained with a symmetric contrastive objective. A public CUFS mirror was audited and found to contain "
        "188 usable CUHK sketch-photo pairs rather than the 606 pairs advertised in its description. We therefore evaluate only the CUFS CUHK subset, "
        "using 114 training, 37 validation, and 37 test identities. Against all 37 held-out photos, the primary model achieves "
        f"{r1}% rank-1, {r5}% rank-5, and {r10}% rank-10 accuracy, compared with {b1}% rank-1 for a frozen pretrained baseline. "
        f"Across three training seeds, rank-1 is {pct(seeds['rank_1']['mean'])}% with a sample standard deviation of "
        f"{pct(seeds['rank_1']['std'])} percentage points. These findings support the value of paired fine-tuning under this small closed-set protocol, "
        "but do not establish performance on full CUFS, large galleries, eyewitness sketches, or composite forensic sketches."
    )
    sections = [
        (
            "I Introduction",
            [
                (
                    "A sketch-based face retrieval system receives a drawing and searches a gallery of photographs for the same person. "
                    "The output is an ordered candidate list rather than a generated face image or a class from a fixed set of training identities. "
                    "The central challenge is domain shift: pencil strokes emphasize contours, whereas photographs contain illumination, texture, and color. "
                    "Features that separate people within photographs may not remain stable in drawings. A useful embedding must retain identity-related structure while reducing sensitivity to modality."
                ),
                (
                    "The project objective is to implement, test, and document a reproducible cross-modal matcher with rank-k evaluation. "
                    "Its contributions are engineering and experimental: explicit data-pair auditing, identity-disjoint partitions, a lightweight shared-encoder model, "
                    "a controlled frozen-feature baseline, repeated training seeds, an adapter ablation, and an application that uses the same inference path as evaluation. "
                    "The architecture combines established methods; no novel algorithm or state-of-the-art performance is claimed."
                ),
                (
                    "Although motivated by forensic sketch search, the evaluated material consists of viewed artist sketches. Such drawings are made while observing the corresponding photograph, "
                    "unlike sketches reconstructed from witness memory or assembled from facial components. Consequently, the application is a college research prototype and its measured scope must remain explicit."
                ),
            ],
        ),
        (
            "II Related work",
            [
                (
                    "Wang and Tang [1] investigated face photo-sketch synthesis and recognition, providing a foundation for work on matching the two modalities. "
                    "Zhang, Wang, and Tang [2] studied coupled information-theoretic encoding for photo-sketch recognition. These studies motivate learning a representation shared by drawings and photographs rather than relying solely on raw appearance. "
                    "Their published recognition numbers are not used as direct numerical baselines here because training protocols, preprocessing, and gallery composition can differ."
                ),
                (
                    "ResNet [3] provides residual visual representations that can be adapted from large-scale image pretraining to a smaller target dataset. "
                    "Symmetric contrastive alignment, as used for paired modalities in CLIP [4], supplies the form of the bidirectional objective employed here; this project does not use CLIP weights, text inputs, or a language encoder. "
                    "AdamW [5] provides decoupled weight decay for optimization. The present implementation tests whether adapting pretrained image features to genuine sketch-photo pairs improves retrieval under a fixed local protocol."
                ),
            ],
        ),
        (
            "III Dataset audit and experimental split",
            [
                (
                    "Full CUFS is described as 606 identities: 188 CUHK students, 123 AR identities, and 295 XM2VTS identities [1, 2, 6]. "
                    "The official archive page returned HTTP 500 during acquisition. We downloaded public Kaggle mirror version 1 [6] and audited its actual contents instead of accepting the listing total. "
                    "It contained 188 cropped photographs and 188 matching CUHK sketches, original-resolution copies, and 1,194 additional sketches without corresponding photo pairs. "
                    "AR and XM2VTS pairs were unavailable in this copy. Only the verified CUHK pairs were included; this experiment is not a full-CUFS benchmark."
                ),
                (
                    "Pairing uses normalized filenames, not directory order. Names are made case-insensitive; the sketch suffix -sz1 is removed; F2-/M2- groups map to the corresponding f-/m- photo groups, while f1-/m1- remain unchanged. "
                    "The resulting 188 one-to-one mappings were checked for readable images, minimum dimensions, exact decoded-pixel duplicates, and identity collisions. "
                    "Representative pairs were inspected visually. A provenance record preserves the download URL, archive checksum, version, exclusions, and original-author rights notice."
                ),
                (
                    "A fixed seed of 42 partitions identities into 114 training, 37 validation, and 37 test subjects. Both images of each subject stay in one split. "
                    "This is a custom 60/20/20 split with integer rounding, not an official published CUFS protocol. The manifest records every identity, source, split, image path, and SHA-256. "
                    "Input files are rechecked before training or evaluation, and checkpoints must match the manifest fingerprint. This prevents accidental reuse of training identities or changed files in the reported test."
                ),
            ],
        ),
        (
            "IV Proposed system",
            [
                (
                    "Images are corrected for EXIF orientation, converted to RGB, then to three-channel grayscale, resized from the supplied 200 by 250 face crops to 224 by 224, "
                    "and normalized using the ImageNet mean and standard deviation. The same deterministic preprocessing is used for validation, testing, and application inference. "
                    "Training adds paired horizontal flips and independent small affine perturbations: rotation up to five degrees and translation up to 2.5 percent. "
                    "No landmark detector or automatic alignment is implemented; uploaded inputs should already be comparably cropped."
                ),
                (
                    "For modality m, the input is transformed as x + A_m(x), where A_m is a zero-initialized 1 by 1 convolution with three input and output channels and no bias. "
                    "The two adapters contain 18 parameters in total and initially act as identity mappings. A shared ResNet-18 [3] produces a 512-dimensional pooled feature. "
                    "The projection head applies Linear(512,256), ReLU, and Linear(256,256). L2 normalization places the final embeddings on the unit hypersphere. "
                    "These small adapters adjust channel combinations; they do not reconstruct a photo or align facial landmarks."
                ),
                (
                    "Let S and P be matrices of normalized sketch and photo embeddings for B distinct paired identities. Similarity logits are L = S P^T / tau, with tau = 0.07. "
                    "The target label for row i is i. The loss is one half of CE(L, labels) plus CE(L^T, labels), following a symmetric paired contrastive formulation [4]. "
                    "Matched pairs are positives and other identities in the batch are negatives. At inference, cosine similarity z_sketch dot z_photo ranks candidates; no claim of calibrated identity probability is made."
                ),
            ],
        ),
        (
            "V Experimental setup",
            [
                (
                    "All trained models run for 20 epochs with batch size 32, AdamW [5], weight decay 0.0001, and gradient norm clipping at 5. "
                    "Adapters and projection use learning rate 0.0003; the encoder uses 0.00003. Epochs 1 through 3 freeze the full encoder. "
                    "Epochs 4 through 20 unfreeze only its final residual stage. Batch-normalization running statistics remain frozen to reduce instability on the small dataset. "
                    "The best checkpoint maximizes validation rank-1; ties are broken by validation mean reciprocal rank, then the earlier epoch. Test results are never used for selection."
                ),
                (
                    "The frozen baseline uses ImageNet-1K V1 ResNet-18 weights, identical preprocessing, and raw L2-normalized 512-dimensional features without adapters or projection. "
                    "The main matcher is trained with seeds 42, 43, and 44 on the same identity split. Seed 42 is designated as primary before test evaluation. "
                    "The adapter ablation uses seed 42 and retains the same projection, optimization, and schedule while bypassing both input adapters. "
                    "The experiment matrix is saved before repeated training and evaluation. Experiments ran locally using Apple MPS; software versions and checkpoint hashes are retained in machine-readable outputs."
                ),
                (
                    "Each of the 37 test sketches is compared against all 37 test photographs. Rank-k is the fraction of queries whose correct match appears in the first k candidates; "
                    "CMC computes this fraction at each rank. Every tied distractor counts ahead of the correct photo, preventing optimistic tie handling. "
                    "Query-level 95 percent percentile bootstrap intervals use 2,000 resamples. The primary-minus-baseline rank-1 difference uses 10,000 paired query resamples. "
                    "Training-seed mean and sample standard deviation are reported separately from these fixed-checkpoint intervals."
                ),
            ],
        ),
        (
            "VI Results and discussion",
            [
                (
                    f"Table I reports every predeclared run. The primary model correctly ranks 27 of 37 photos first ({r1}%), compared with 10 of 37 ({b1}%) for the baseline. "
                    f"Its rank-5 and rank-10 accuracies are {r5}% and {r10}%, corresponding to 33 and 37 successful queries. "
                    f"The rank-1 bootstrap interval is [{pct(low)}%, {pct(high)}%]. The absolute rank-1 gain is {pct(delta['estimate'])} percentage points, "
                    f"with paired bootstrap interval [{pct(delta['ci95'][0])}, {pct(delta['ci95'][1])}] percentage points. "
                    "The matcher recovers 19 queries missed at rank 1 by the baseline, while losing 2 that the baseline ranked correctly. This supports a benefit from paired training in this fixed experiment."
                ),
                (
                    f"The three matcher runs achieve rank-1 values of {', '.join(pct(v) + '%' for v in seeds['rank_1']['values'])}. "
                    f"The mean is {pct(seeds['rank_1']['mean'])}% and sample standard deviation is {pct(seeds['rank_1']['std'])} percentage points. "
                    "The repeated seeds share the same training and test identities; they quantify optimization variation rather than generalization across independent splits. "
                    "The primary model was selected at epoch 20, the final allowed epoch. This does not demonstrate convergence or imply that 20 epochs are optimal."
                ),
                (
                    "The no-adapter model reaches 67.57 percent rank-1 and 97.30 percent rank-5. Thus, the primary adapter run improves rank-1 by 5.41 percentage points but has lower rank-5 than the ablation. "
                    "One ablation seed cannot establish a reliable benefit from adapters, and the observed pattern does not support describing them as uniformly better. "
                    "The defensible finding is that fine-tuning and projection improve on frozen generic features; the adapters require further controlled investigation."
                ),
                (
                    "Ten primary queries fail at rank 1, although every correct match appears by rank 10. The hardest correct match is at rank 10. "
                    "The CMC comparison and training curves accompany the report. Falling contrastive loss and increasing validation retrieval are consistent with learning, but do not eliminate overfitting concerns. "
                    "Rank-10 reaches a bootstrap interval of [100,100] percent because every observed query succeeds; this boundary result is not evidence of perfect performance on future identities."
                ),
            ],
        ),
        (
            "VII Limitations and responsible interpretation",
            [
                (
                    "The strongest limitation is dataset coverage. Only the CUHK subset is paired and evaluated; AR and XM2VTS, unseen-source transfer, and the complete 606-identity benchmark remain untested. "
                    "The test contains just 37 identities, so one query changes accuracy by approximately 2.70 percentage points. The gallery is fixed and closed set, making the task easier than searching a large operational database that may not contain the person."
                ),
                (
                    "Bootstrap intervals condition on the available gallery and checkpoint. They do not account for demographic coverage, independent sampling of galleries, differences between sketch artists, or witness-memory distortion. "
                    "ImageNet pretraining is declared, but potential identity overlap has not been independently audited. The dataset does not support a meaningful demographic fairness claim. "
                    "Retrieval scores must not be used as identity verification, evidence of guilt, or an automatic decision about a person."
                ),
                (
                    "Further work should obtain the complete CUFS sources through their owners, predefine larger-gallery and leave-one-source-out protocols, "
                    "repeat ablations across seeds and splits, and evaluate on an appropriate forensic sketch dataset. "
                    "Unknown-person rejection would require a separate open-set evaluation and validation-selected thresholds. Gallery-feature caching and automatic face alignment are engineering extensions, not completed experiments."
                ),
            ],
        ),
        (
            "VIII Conclusion",
            [
                (
                    f"Sketch2Face provides a working cross-modal matcher, reproducible experiment pipeline, retrieval application, and rank-k report based on actual data. "
                    f"On a 37-photo held-out gallery drawn from 188 CUHK identities, the primary model achieves {r1}% rank-1 compared with {b1}% for frozen pretrained features. "
                    f"The three-seed rank-1 mean is {pct(seeds['rank_1']['mean'])}%. "
                    "These results support paired representation learning under this restricted protocol. They do not validate the entire CUFS benchmark or real forensic deployment. "
                    "The archive audit and recorded experimental limits are part of the findings, not details to omit from the final submission."
                )
            ],
        ),
    ]
    return abstract, sections


def doc_styles(document, paper=False):
    # Word's default Title style can inherit a decorative blue paragraph border.
    for style in document.styles:
        for border in list(style.element.iter(qn("w:pBdr"))):
            border.getparent().remove(border)
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.2677), Inches(11.6929)
    section.top_margin = Inches(0.7 if paper else 0.85)
    section.bottom_margin = Inches(0.7 if paper else 0.85)
    section.left_margin = Inches(0.65 if paper else 1.15)
    section.right_margin = Inches(0.65 if paper else 0.85)
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10 if paper else 12)
    normal.paragraph_format.line_spacing = 1.06 if paper else 1.3
    normal.paragraph_format.space_after = Pt(5 if paper else 8)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for name, size in [
        ("Title", 18 if paper else 25),
        ("Heading 1", 11 if paper else 18),
        ("Heading 2", 10 if paper else 14),
    ]:
        style = document.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = True
    document.core_properties.author = STUDENT
    document.core_properties.title = TITLE
    document.core_properties.subject = "College project on cross-modal sketch-photo retrieval"
    if not paper:
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), "PAGE")
        footer._p.append(field)


def word_table(document, rows, paper=False):
    table = document.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    if paper:
        table.autofit = False
        widths = [1.15, 0.55, 0.55, 0.55, 0.55]
        for column, width in zip(table.columns, widths):
            column.width = Inches(width)
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        if paper:
            for cell, width in zip(cells, widths):
                cell.width = Inches(width)
        for cell, text in zip(cells, row):
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(str(text))
            run.font.size = Pt(8 if paper else 10)
            run.bold = i == 0
        props = table.rows[-1]._tr.get_or_add_trPr()
        props.append(OxmlElement("w:cantSplit"))
        if i == 0:
            props.append(OxmlElement("w:tblHeader"))
    document.add_paragraph()


def add_image(document, filename, caption, paper=False):
    document.add_picture(str(FIG / filename), width=Inches(3.35 if paper else 6.0))
    p = document.add_paragraph(caption)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in p.runs:
        run.italic = True
        run.font.size = Pt(8 if paper else 10)


def build_word(summary, abstract, sections):
    report = Document()
    doc_styles(report)
    for text, size, bold in [
        (UNIVERSITY, 24, True),
        ("College project report", 16, False),
        (TITLE, 23, True),
        ("Submitted by", 13, False),
        (STUDENT, 18, True),
        ("Roll number: " + ROLL, 12, False),
        (PROGRAMME, 13, False),
        ("Under the guidance of", 12, False),
        (GUIDE, 13, False),
        ("Academic period " + YEARS, 13, False),
    ]:
        p = report.add_paragraph(style="Title" if text == TITLE else "Normal")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(15)
        r = p.add_run(text)
        r.font.size, r.bold = Pt(size), bold
    report.add_paragraph(
        "Experimental scope: CUFS CUHK subset - 188 verified identities. Research prototype.",
        style="Normal",
    )
    report.add_page_break()
    report.add_heading("Abstract", 1)
    report.add_paragraph(abstract)
    report.add_heading("Keywords", 2)
    report.add_paragraph(
        "Sketch-photo matching; cross-modal embeddings; contrastive learning; CUFS; rank-k retrieval; ResNet-18."
    )
    report.add_heading("Submission details", 2)
    report.add_paragraph(
        "The roll number and guide fields are marked placeholders and must be replaced before submission. The findings are based on completed local experiments. No approval certificate or signed declaration is included."
    )
    report.add_page_break()
    report.add_heading("Contents", 1)
    chapter_titles = [
        "1 Problem statement and objectives",
        "2 Literature review",
        "3 Dataset acquisition and audit",
        "4 Requirements and system design",
        "5 Methodology and implementation",
        "6 Experimental protocol",
        "7 Results and analysis",
        "8 Testing and demonstration",
        "9 Limitations and future work",
        "10 Conclusion",
        "References",
        "Appendix Reproduction and evidence",
    ]
    for title in chapter_titles:
        report.add_paragraph(title)
    chapters = [
        (chapter_titles[0], sections[0][1]),
        (chapter_titles[1], sections[1][1]),
        (chapter_titles[2], sections[2][1]),
        (
            chapter_titles[3],
            [
                "Functional requirements are explicit sketch-photo pairing, duplicate detection, frozen identity splits, model training, validation checkpoint selection, photo ranking, and rank-k reporting. The application must accept a query sketch and candidate photos, show an ordered shortlist, and export scores without presenting them as identity probabilities.",
                "The implementation uses Python, PyTorch, torchvision, Pillow, NumPy, Matplotlib, and Streamlit. Training supports CUDA, Apple MPS, or CPU. Academic artifacts use python-docx, python-pptx, and reportlab. The repository includes a dependency lockfile, unit tests, deterministic split settings, saved model configurations, and provenance checks.",
                "The system consists of a data layer, paired-image dataset, cross-modal encoder, training/evaluation engine, metric module, command-line interface, and local demonstration interface. Dataset paths and model weights remain local. Public source includes experiment metrics and charts but excludes raw face images and the Python environment.",
                "A 224 by 224 grayscale-RGB tensor is the input. A 256-dimensional normalized vector is the trained output. For N gallery photos, the query is compared with N embeddings. Gallery features are currently recomputed at each search; indexed caching is a possible extension.",
            ],
        ),
        (chapter_titles[4], sections[3][1] + sections[4][1][:1]),
        (
            chapter_titles[5],
            sections[4][1][1:]
            + [
                "The 114/37/37 split is held constant across all runs. The primary seed is 42 and repeated training seeds are 43 and 44. A no-adapter seed-42 run tests one architectural component. The baseline and ablation use the same gallery, preprocessing, and identity partition as the primary model. Every run is reported; the best test seed is not substituted for the designated primary result."
            ],
        ),
        (chapter_titles[6], sections[5][1]),
        (
            chapter_titles[7],
            [
                "Automated checks cover deterministic and disjoint splits, duplicate-image rejection, changed-file detection, checkpoint round-tripping, normalized embeddings, valid contrastive gradients, known retrieval ranks, shuffled gallery order, pessimistic tie handling, and invalid score inputs. Streamlit application tests execute the real held-out gallery workflow and verify that upload mode loads.",
                "For the viva demonstration, start Streamlit, select the primary matcher checkpoint, choose a held-out sketch, and run retrieval. Explain that every test identity was excluded from training and validation, while the correct photo is intentionally present in the closed-set gallery. Show the correct rank and download the ordered JSON results. Then switch to upload mode to demonstrate the input workflow.",
                "To reproduce numeric findings, run the dataset downloader, fixed experiment script, and figure builder. The primary checkpoint is runs/matcher/best.pt; result summaries are stored in outputs/results/summary.json. Model settings, chosen epochs, query ranks, image hashes, and checkpoint hashes permit independent inspection of the evidence.",
            ],
        ),
        (chapter_titles[8], sections[6][1]),
        (chapter_titles[9], sections[7][1]),
    ]
    for index, (title, paragraphs) in enumerate(chapters):
        report.add_page_break()
        report.add_heading(title, 1)
        for paragraph in paragraphs:
            report.add_paragraph(paragraph)
        if index == 2:
            word_table(
                report,
                [
                    ["Source", "Full CUFS description", "Verified pairs used"],
                    ["CUHK", "188", "188"],
                    ["AR", "123", "0"],
                    ["XM2VTS", "295", "0"],
                    ["Total", "606", "188"],
                ],
            )
        if index == 3:
            word_table(
                report,
                [
                    ["Module", "Responsibility"],
                    ["data.py", "Pair audit, preprocessing, immutable manifest"],
                    ["model.py", "Adapters, shared encoder, projection, loss"],
                    ["engine.py", "Training, validation, retrieval, evaluation"],
                    ["metrics.py", "Ranks, CMC, confidence intervals"],
                    ["app.py", "Local gallery search demonstration"],
                ],
            )
        if index == 5:
            word_table(
                report,
                [
                    ["Setting", "Value"],
                    ["Identity split", "114 train / 37 validation / 37 test"],
                    ["Training epochs / batch size", "20 / 32"],
                    ["Temperature / embedding size", "0.07 / 256"],
                    ["Learning rate: head / backbone", "3e-4 / 3e-5"],
                    ["Warmup / fine-tuning", "3 epochs / final residual stage"],
                    ["Pretraining", "ResNet-18 ImageNet-1K V1"],
                ],
            )
        if index == 6:
            word_table(report, metrics_table(summary))
            add_image(
                report, "cmc_comparison.png", "Figure 1 CMC on the same 37-photo held-out gallery"
            )
            add_image(
                report,
                "learning_curves.png",
                "Figure 2 Primary training loss and validation rank-1; dashed line marks fine-tuning start",
            )
    report.add_page_break()
    report.add_heading("References", 1)
    for reference in REFERENCES:
        report.add_paragraph(reference)
    report.add_page_break()
    report.add_heading("Appendix Reproduction and evidence", 1)
    for line in [
        "Install: uv sync --extra dev --extra documents",
        "Download: uv run python scripts/download_cufs.py",
        "Experiment: uv run python scripts/run_experiments.py",
        "Figures: uv run python scripts/make_figures.py",
        "Artifacts: uv run python scripts/build_academic.py",
        "Tests: uv run pytest -q",
        "Demo: uv run streamlit run app.py",
        "Core evidence: outputs/results/summary.json; outputs/manifest.json; outputs/data_provenance.json; outputs/experiment_protocol.json.",
        "Per-run evidence: metrics.json, retrievals.json, similarities.npz, history.json, checkpoint SHA-256 and selected epoch.",
        "Finding traceability: audited archive and manifest establish the 188-identity scope; fixed test scores establish the rank-k table; repeated seed metrics establish optimization variation; adapter ablation establishes the mixed rank-1/rank-5 effect.",
        "Before submission: replace roll and guide placeholders; verify department formatting requirements; rehearse the distinction between the 188-identity subset and full CUFS; keep the local data and checkpoints available for the demonstration.",
    ]:
        report.add_paragraph(line)
    report.save(OUT / "project_report.docx")
    report_md = [
        "# " + TITLE,
        "",
        UNIVERSITY,
        PROGRAMME,
        STUDENT,
        "Roll: " + ROLL,
        "Guide: " + GUIDE,
        "Academic period: " + YEARS,
        "",
        "## Abstract",
        abstract,
    ]
    for title, paragraphs in chapters:
        report_md.extend(["", "## " + title, "", "\n\n".join(paragraphs)])
    report_md.extend(["", "## References", "\n\n".join(REFERENCES)])
    (OUT / "project_report.md").write_text("\n\n".join(report_md) + "\n")

    paper = Document()
    doc_styles(paper, paper=True)
    p = paper.add_paragraph(TITLE, style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for line in [STUDENT, PROGRAMME, UNIVERSITY + ", Punjab, India"]:
        p = paper.add_paragraph(line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
    sec = paper.add_section(WD_SECTION_START.CONTINUOUS)
    columns = sec._sectPr.find(qn("w:cols"))
    columns.set(qn("w:num"), "2")
    columns.set(qn("w:space"), "300")
    paper.add_paragraph("Abstract - " + abstract)
    paper.add_paragraph(
        "Keywords - Sketch-photo retrieval; cross-modal learning; CUFS; contrastive loss; rank-k."
    )
    for index, (title, paragraphs) in enumerate(sections):
        paper.add_heading(title, 1)
        for paragraph in paragraphs:
            paper.add_paragraph(paragraph)
        if index == 5:
            caption = paper.add_paragraph(
                "Table I Retrieval accuracy on the same 37-photo test gallery"
            )
            caption.paragraph_format.keep_with_next = True
            word_table(paper, metrics_table(summary), paper=True)
            add_image(
                paper,
                "cmc_comparison.png",
                "Figure 1 Test CMC for the baseline, primary matcher, and ablation",
                paper=True,
            )
    paper.add_heading("References", 1)
    for reference in REFERENCES:
        paper.add_paragraph(reference)
    paper.save(OUT / "research_paper.docx")
    md = ["# " + TITLE, "", STUDENT + " | " + UNIVERSITY, "", "## Abstract", abstract]
    for title, paragraphs in sections:
        md.extend(["", "## " + title, "", "\n\n".join(paragraphs)])
        if title.startswith("VI "):
            rows = metrics_table(summary)
            md.extend(["", "| " + " | ".join(rows[0]) + " |", "|---|---:|---:|---:|---:|"])
            md.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    md.extend(["", "## References", "\n\n".join(REFERENCES)])
    (OUT / "research_paper.md").write_text("\n\n".join(md) + "\n")


def paper_pdf(summary, abstract, sections):
    width, height = A4
    margin, gap = 42, 18
    column = (width - 2 * margin - gap) / 2
    body = ParagraphStyle(
        "Body",
        fontName="Times-Roman",
        fontSize=9.5,
        leading=11.5,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    heading = ParagraphStyle(
        "Head",
        parent=body,
        fontName="Times-Bold",
        fontSize=10,
        alignment=TA_CENTER,
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True,
    )
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=9.5)
    title = ParagraphStyle(
        "Title", fontName="Times-Bold", fontSize=18, leading=21, alignment=TA_CENTER
    )
    doc = BaseDocTemplate(str(OUT / "research_paper.pdf"), pagesize=A4, title=TITLE, author=STUDENT)

    def header(canvas, document):
        canvas.setFont("Times-Roman", 8)
        canvas.drawCentredString(width / 2, 23, str(document.page))
        if document.page == 1:
            p = Paragraph(escape(TITLE), title)
            _, h = p.wrap(width - 2 * margin, 80)
            p.drawOn(canvas, margin, height - 42 - h)
            canvas.setFont("Times-Roman", 10)
            canvas.drawCentredString(width / 2, height - 105, STUDENT)
            canvas.setFont("Times-Roman", 9)
            canvas.drawCentredString(width / 2, height - 118, PROGRAMME)
            canvas.drawCentredString(width / 2, height - 130, UNIVERSITY + ", Punjab, India")

    def frames(top):
        return [
            Frame(
                margin + i * (column + gap),
                42,
                column,
                top - 42,
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )
            for i in range(2)
        ]

    doc.addPageTemplates(
        [
            PageTemplate(
                id="First", frames=frames(height - 151), onPage=header, autoNextPageTemplate="Rest"
            ),
            PageTemplate(id="Rest", frames=frames(height - 42), onPage=header),
        ]
    )
    story = [
        Paragraph("<b>Abstract - </b>" + escape(abstract), body),
        Paragraph(
            "<b>Keywords - </b>Sketch-photo retrieval; cross-modal embeddings; CUFS; contrastive learning; rank-k.",
            small,
        ),
    ]
    for index, (name, paragraphs) in enumerate(sections):
        story.append(Paragraph(escape(name), heading))
        story.extend(Paragraph(escape(p), body) for p in paragraphs)
        if index == 5:
            story.append(Paragraph("TABLE I. TEST RETRIEVAL ACCURACY (37 PHOTOS)", small))
            rows = [
                [Paragraph(escape(cell), small) for cell in row] for row in metrics_table(summary)
            ]
            table = Table(rows, colWidths=[column * v for v in [0.38, 0.13, 0.16, 0.16, 0.17]])
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf3f5")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story += [
                table,
                Spacer(1, 8),
                Image(str(FIG / "cmc_comparison.png"), width=column, height=column * 4.2 / 7.2),
                Paragraph(
                    "Fig. 1. CMC on the same held-out gallery. The primary run is fixed as seed 42.",
                    small,
                ),
            ]
    story.append(Paragraph("References", heading))
    story.extend(Paragraph(escape(p), small) for p in REFERENCES)
    doc.build(story)


def build_slides(summary):
    prs = Presentation()
    prs.slide_width, prs.slide_height = PI(13.333), PI(7.5)
    navy, teal, ink, muted = "122337", "087F8C", "1A2733", "526575"

    def textbox(slide, text, x, y, w, h, size=24, color=ink, bold=False):
        shape = slide.shapes.add_textbox(PI(x), PI(y), PI(w), PI(h))
        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        for i, line in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.name = "Aptos"
            p.font.size, p.font.bold, p.font.color.rgb = PP(size), bold, PptColor.from_string(color)
            p.space_after = PP(16)
        return shape

    def slide(title, lines=None, note="", image=None):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = PptColor.from_string("FFFFFF")
        textbox(s, title, 0.65, 0.45, 12.0, 1.0, 34, navy, True)
        if lines:
            textbox(s, "\n".join(lines), 0.7, 1.85, 11.9, 4.8, 25)
        if image:
            s.shapes.add_picture(str(FIG / image), PI(1.4), PI(1.7), width=PI(10.4), height=PI(5.0))
        textbox(s, str(len(prs.slides)), 12.2, 7.05, 0.5, 0.3, 12, muted)
        s.notes_slide.notes_text_frame.text = note
        return s

    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = PptColor.from_string(navy)
    textbox(s, "Sketch2Face", 0.75, 1.05, 11.5, 1.0, 52, "FFFFFF", True)
    textbox(s, "Cross-modal face retrieval\nCUFS CUHK subset", 0.8, 2.3, 11.6, 1.6, 31, "BCE6E8")
    textbox(
        s,
        STUDENT
        + "  |  Roll: "
        + ROLL
        + "\n"
        + PROGRAMME
        + "\n"
        + UNIVERSITY
        + "  |  "
        + YEARS
        + "\nGuide: "
        + GUIDE,
        0.8,
        4.65,
        11.6,
        2.2,
        18,
        "FFFFFF",
    )
    s.notes_slide.notes_text_frame.text = "Introduce the project as sketch-to-photo retrieval. Replace the two marked placeholders before submission. All numeric results come from completed local experiments."
    slide(
        "Problem and objective",
        [
            "Input: one face sketch and a gallery of candidate photos",
            "Output: photos ranked by similarity to the person in the sketch",
            "Challenge: preserve identity across pencil strokes and photographic appearance",
            "Objective: build the matcher and measure rank-k retrieval accuracy",
        ],
        note="This is a retrieval project, not a face generation project. Training identities differ from test identities. Motivation is forensic search, but the evaluation uses viewed artist sketches.",
    )
    slide(
        "Dataset audit",
        [
            "Full CUFS description: 606 identities across CUHK, AR, and XM2VTS",
            "Downloaded mirror: 188 usable CUHK sketch-photo pairs",
            "Extra unpaired sketches and duplicate original files were excluded",
            "Every reported result is for the verified CUHK subset",
        ],
        note="Sources: references [1], [2], [6]. Official archive returned HTTP 500. Public mirror version 1 has 188 files in photos and 188 files in sketches. Archive checksum and mapping rules are in outputs/data_provenance.json.",
    )
    slide(
        "Identity-disjoint evaluation",
        [
            "114 training identities: learn sketch-photo correspondence",
            "37 validation identities: select the checkpoint",
            "37 test identities: final held-out experiment",
            "Each test sketch searches all 37 held-out photos",
        ],
        note="Split seed 42, one pair per identity, custom 60/20/20 split with floor rounding. Both images of each person stay in the same split. The correct photo is present by design: this is closed-set evaluation.",
    )
    s = slide(
        "Model architecture",
        note="ResNet-18: He et al. [3]. The adapters are residual 1x1 convolutions, zero-initialized. There are only 18 adapter parameters total. No face detector, landmark alignment, photo synthesis, or language model is used.",
    )
    rows = [
        ["Stage", "Operation", "Output"],
        ["Preprocessing", "Grayscale, resize, normalize", "3 x 224 x 224"],
        ["Modality input", "Sketch or photo residual adapter", "3 x 224 x 224"],
        ["Shared encoder", "ImageNet-pretrained ResNet-18", "512 features"],
        ["Projection", "Linear, ReLU, Linear, normalize", "256-D embedding"],
        ["Retrieval", "Cosine similarity to gallery", "Ranked photos"],
    ]
    native_table(s, rows, 0.7, 1.8, 11.9, 4.7)
    slide(
        "Paired contrastive learning",
        [
            "A batch contains sketches and photos of distinct paired identities",
            "Correct sketch-photo pairs are positives; other people are negatives",
            "Learn in both directions: sketch to photo and photo to sketch",
            "L = 0.5 x [CE(S Pᵀ / τ) + CE(P Sᵀ / τ)],  τ = 0.07",
        ],
        note="The diagonal pair indices are the cross-entropy targets. S and P are L2-normalized embeddings. The symmetric paired objective follows the form used in CLIP [4]; no CLIP weights or text encoder are used. Similarity is not an identity probability.",
    )
    slide(
        "Training and comparisons",
        [
            "20 epochs; batch size 32; AdamW optimization",
            "Freeze backbone for 3 epochs, then fine-tune the final residual stage",
            "Compare frozen baseline, trained matcher, and no-adapter ablation",
            "Repeat matcher training with seeds 42, 43, and 44",
        ],
        note="Learning rates: 3e-4 projection/adapters and 3e-5 encoder; weight decay 1e-4. Frozen BatchNorm statistics. Checkpoint selection uses validation rank-1, then MRR. Primary seed fixed at 42. Test never selects the model. AdamW: [5].",
    )
    s = slide(
        "Measured retrieval accuracy",
        note="All values are percentages on the same 37-photo test gallery. Epoch is selected using validation. Source: outputs/results/summary.json. All predeclared runs are included.",
    )
    native_table(s, metrics_table(summary), 0.7, 1.8, 11.9, 4.4)
    slide(
        "CMC comparison",
        image="cmc_comparison.png",
        note="Source: actual CMC arrays in per-run metrics.json. CMC is the fraction of correct photos found by rank k. The primary model reaches 100 percent at rank 10 within this gallery; this does not predict accuracy on larger galleries.",
    )
    s = slide(
        "Rank-k comparison",
        note="Editable native PowerPoint chart. Source: outputs/results/summary.json. The primary model has higher rank-1, while the no-adapter ablation has higher rank-5. Both reach 100 percent rank-10 on these observed queries.",
    )
    data = CategoryChartData()
    data.categories = ["Rank-1", "Rank-5", "Rank-10"]
    for key, name in [
        ("baseline", "Frozen baseline"),
        ("matcher", "Trained matcher"),
        ("shared_input", "Without adapters"),
    ]:
        data.add_series(
            name,
            [
                summary["runs"][key]["overall"]["metrics"][f"rank_{k}"]["accuracy"] * 100
                for k in (1, 5, 10)
            ],
        )
    chart = s.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, PI(0.8), PI(1.75), PI(11.8), PI(4.9), data
    ).chart
    # python-pptx emits signed axis IDs; OOXML readers may require unsigned values.
    for element in chart._chartSpace.iter():
        if element.tag.rsplit("}", 1)[-1] in ("axId", "crossAx"):
            value = int(element.get("val"))
            if value < 0:
                element.set("val", str(value + 2**32))
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.font.size = PP(16)
    chart.value_axis.minimum_scale, chart.value_axis.maximum_scale = 0, 100
    chart.value_axis.tick_labels.font.size = PP(16)
    chart.category_axis.tick_labels.font.size = PP(18)
    for series, color in zip(chart.series, ["7B8794", teal, "C27A29"]):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = PptColor.from_string(color)
    slide(
        "What the experiments show",
        [
            "Primary rank-1: 27 correct queries out of 37 (72.97%)",
            "Frozen baseline: 10 correct queries out of 37 (27.03%)",
            "Paired rank-1 gain: 45.95 percentage points; 95% interval 27.03–64.86",
            "Three-seed mean rank-1: 69.37% ± 3.12 percentage points",
        ],
        note="The gain interval uses 10000 paired query bootstrap samples. The ± quantity is sample standard deviation across three training seeds, not a confidence interval. The primary model recovers 19 baseline failures and loses two baseline successes.",
    )
    slide(
        "Adapter ablation and errors",
        [
            "Without adapters: 67.57% rank-1, 97.30% rank-5",
            "Adapters improve primary rank-1, but reduce rank-5 in this comparison",
            "Ten primary queries fail at rank 1; the hardest correct match is rank 10",
            "One ablation seed does not establish a consistent adapter benefit",
        ],
        note="Source: summary.json and matcher/retrievals.json. Do not claim that the adapters explain all improvement. The safer finding is the benefit of the trained representation relative to generic frozen features. Demonstrate actual failures in the local app instead of embedding dataset photos in the public deck.",
    )
    slide(
        "Learning curves",
        image="learning_curves.png",
        note="Source: runs/matcher/history.json copied into outputs/results/matcher/history.json. The dashed line separates warmup and layer-4 fine-tuning. The selected primary epoch is 20, at the training budget boundary, so optimal duration and convergence are not established.",
    )
    slide(
        "Limitations",
        [
            "Only the CUHK subset; AR and XM2VTS pairs remain untested",
            "Small closed-set gallery: 37 photos; no unknown-person rejection",
            "Viewed artist sketches differ from eyewitness and composite sketches",
            "No demographic fairness, forensic reliability, or state-of-the-art claim",
        ],
        note="Each test success changes accuracy by 2.70 percentage points. Bootstrap intervals condition on this fixed gallery. A 100 percent observed rank-10 result is not proof of perfect future retrieval. Pretraining identity overlap was not independently audited.",
    )
    slide(
        "Demo and conclusion",
        [
            "Run: uv run streamlit run app.py",
            "Select a held-out sketch, rank the gallery, and inspect the correct rank",
            "Paired training substantially improves the measured frozen baseline",
            "Next: full CUFS, larger galleries, repeated ablations, forensic datasets",
        ],
        note="The demo uses the exact evaluation preprocessing and model loader. In upload mode the user supplies candidate photos; the system cannot know whether the person is present. Scores are similarities only. Dataset and weights remain local; code, metrics, and documentation are reproducible from the public repository.",
    )
    slide(
        "References",
        [
            "Wang & Tang, Photo-Sketch Synthesis and Recognition, TPAMI 2009",
            "Zhang et al., Coupled Information-Theoretic Encoding, CVPR 2011",
            "He et al., Deep Residual Learning, CVPR 2016",
            "Radford et al., Contrastive multimodal learning, ICML 2021",
            "Loshchilov & Hutter, AdamW, ICLR 2019; CUFS mirror, Kaggle v1",
        ],
        note="Full citations and access URLs:\n" + "\n".join(REFERENCES),
    )
    prs.save(OUT / "presentation.pptx")
    notes = []
    for i, s in enumerate(prs.slides, 1):
        texts = [shape.text for shape in s.shapes if shape.has_text_frame]
        notes += [f"## Slide {i} - {texts[0]}", s.notes_slide.notes_text_frame.text]
    (OUT / "presentation_notes.md").write_text("\n\n".join(notes) + "\n")


def native_table(slide, rows, x, y, width, height):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), PI(x), PI(y), PI(width), PI(height))
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            cell = shape.table.cell(i, j)
            cell.text = str(text)
            cell.fill.solid()
            cell.fill.fore_color.rgb = PptColor.from_string(
                "122337" if i == 0 else ("EDF4F5" if i % 2 else "FFFFFF")
            )
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.name = "Aptos"
                paragraph.font.size = PP(19 if len(rows[0]) > 3 else 21)
                paragraph.font.bold = i == 0
                paragraph.font.color.rgb = PptColor.from_string("FFFFFF" if i == 0 else "1A2733")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = json.loads((ROOT / "outputs/results/summary.json").read_text())
    abstract, sections = content(summary)
    build_word(summary, abstract, sections)
    paper_pdf(summary, abstract, sections)
    build_slides(summary)
    viva = [
        (
            "What does the project do?",
            "Given a face sketch, it ranks candidate photos by similarity to the same identity.",
        ),
        (
            "Why is this cross-modal?",
            "The query is a drawing and the gallery contains photographs; their appearance statistics differ.",
        ),
        (
            "Is it a photo generator?",
            "No. It learns vectors for retrieval, without generating face photos.",
        ),
        (
            "Why use pretrained ResNet-18?",
            "The small paired dataset is insufficient to train a strong visual backbone from scratch. ImageNet features provide a starting representation.",
        ),
        (
            "What are embeddings?",
            "Numerical feature vectors. Here trained outputs have 256 dimensions and unit length.",
        ),
        (
            "What is the loss?",
            "Average of sketch-to-photo and photo-to-sketch cross-entropy over batch cosine similarities, with matched pairs on the diagonal.",
        ),
        (
            "How is leakage avoided?",
            "Split identities before augmentation; keep each sketch and photo together; verify file hashes and require checkpoint-manifest agreement.",
        ),
        (
            "What exactly was tested?",
            "188 CUHK identities split 114/37/37. Each test sketch retrieves from all 37 held-out photos. This is a custom subset protocol.",
        ),
        (
            "Why not say full CUFS?",
            "The downloaded mirror lacks paired AR and XM2VTS photos. Its 606-pair listing does not match its actual usable contents.",
        ),
        (
            "What did we find?",
            "Primary rank-1 is 72.97%, baseline 27.03%; the three-seed matcher mean is 69.37% ± 3.12 percentage points.",
        ),
        (
            "What is rank-5?",
            "The fraction of queries whose correct photograph is anywhere in the first five results.",
        ),
        (
            "Do adapters always improve retrieval?",
            "No. In one controlled seed they improve rank-1 but have lower rank-5. More ablation seeds are needed.",
        ),
        (
            "Does 100% rank-10 prove perfect identification?",
            "No. It describes only 37 observed queries in a small closed-set gallery; all correct photos are present.",
        ),
        (
            "Are scores probabilities?",
            "No. They are cosine similarities and are not calibrated identity confidence.",
        ),
        (
            "Can this be deployed by police?",
            "These experiments do not establish forensic reliability. Eyewitness, composite, open-set, and demographic tests are missing.",
        ),
        (
            "What is original about this work?",
            "The project integrates established methods in an audited, reproducible pipeline and evaluates them locally. It does not claim a novel algorithm.",
        ),
        (
            "What should improve next?",
            "Obtain full CUFS through its owners, enlarge galleries, evaluate unseen sources and forensic sketches, repeat ablations, and consider alignment and feature caching.",
        ),
    ]
    (OUT / "viva_guide.md").write_text(
        "# Sketch2Face viva guide\n\n" + "\n\n".join("## " + q + "\n\n" + a for q, a in viva) + "\n"
    )
    print(f"Built academic package in {OUT}")


if __name__ == "__main__":
    main()
