# Experimental evidence and academic submission

The results in this directory come from completed experiments on the **188-identity CUFS CUHK subset**. They are not full-CUFS measurements. Raw dataset images and training checkpoints stay local; clone users can reproduce them using the scripts in the main README.

## Main findings

The primary matcher ranks the correct photo first for 27 of 37 test sketches (72.97%), versus 10 of 37 (27.03%) for frozen ImageNet features. Rank-5 is 89.19%; rank-10 is 100% on this 37-photo gallery. The three-seed rank-1 mean is 69.37%, with sample standard deviation 3.12 percentage points. Adapter ablation is mixed: lower rank-1 but higher rank-5 without adapters. See the paper for uncertainty and limitations.

## Submission files

- `academic/project_report.pdf` and `.docx`: LPU college project report.
- `academic/research_paper.pdf` and `.docx`: IEEE-style research paper.
- `academic/presentation.pptx` and `.pdf`: editable 16-slide presentation and reading copy.
- `academic/presentation_notes.md`: speaker notes with references.
- `academic/viva_guide.md`: questions and answers for the project viva.
- `academic/project_report.md` and `research_paper.md`: editable text sources.

Cover details: Lovely Professional University; B.Tech in Artificial Intelligence and Machine Learning; Ipsita; academic period 2023–2027. Roll number and guide are explicitly marked placeholders.

## Evidence files

`results/summary.json` contains every run, seed aggregation, and paired improvement interval. Individual run directories contain metrics, ranks, query-level results, similarities, and training history. `experiment_protocol.json` records the fixed design; `data_provenance.json` records the acquisition audit; `manifest.json` records the identity split and input hashes.

Manifests and results preserve the original experiment paths for provenance. Those paths are local references, not files distributed in this repository. The dataset must be downloaded and prepared locally for reproduction.

CMC and rank-comparison charts under `figures/` use actual measurements. Local photo example figures are excluded from the public repository because the original authors retain image rights. The public paper, report, and slides contain results charts and no dataset face images.
