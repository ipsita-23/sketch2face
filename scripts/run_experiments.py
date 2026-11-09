"""Run the fixed experiment matrix. Never changes hyperparameters based on test results."""

import json
import shutil
from pathlib import Path

import numpy as np

from sketch2face.data import load_manifest
from sketch2face.engine import evaluate, train, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = load_manifest(ROOT / "data/manifest.json")
    runs = [
        ("baseline", {"baseline": True, "seed": 42}),
        ("matcher", {"seed": 42}),
        ("matcher_seed43", {"seed": 43}),
        ("matcher_seed44", {"seed": 44}),
        ("shared_input", {"seed": 42, "adapters": False}),
    ]
    protocol = {
        "manifest_fingerprint": manifest["fingerprint"],
        "epochs": 20,
        "warmup_epochs": 3,
        "image_size": 224,
        "batch_size": 32,
        "learning_rate": 0.0003,
        "encoder_learning_rate": 0.00003,
        "weight_decay": 0.0001,
        "temperature": 0.07,
        "embedding_dim": 256,
        "checkpoint_selection": "Validation rank-1, then validation MRR; earliest exact tie",
        "primary_run": "matcher",
        "training_seeds": [42, 43, 44],
        "ablation": "shared_input: remove residual modality adapters",
        "runs": [dict(name=name, **options) for name, options in runs],
        "test_policy": "Fixed experiment matrix, evaluated after all runs have completed. No test-driven tuning.",
    }
    write_json(ROOT / "outputs/experiment_protocol.json", protocol)
    for name, options in runs:
        directory = ROOT / "runs" / name
        if (directory / "best.pt").exists() and not options.get("baseline"):
            history_path = directory / "history.json"
            if not history_path.exists() or len(json.loads(history_path.read_text())) != 20:
                raise ValueError(
                    f"Interrupted run detected at {directory}; use a fresh run directory."
                )
        if not (directory / "best.pt").exists():
            print(f"Training {name}", flush=True)
            train(manifest, directory, **options)
    summaries = {}
    for name, _ in runs:
        directory = ROOT / "runs" / name
        evaluation = directory / "test"
        if not (evaluation / "metrics.json").exists():
            evaluate(manifest, directory / "best.pt", evaluation)
        result = json.loads((evaluation / "metrics.json").read_text())
        summaries[name] = result
        target = ROOT / "outputs/results" / name
        target.mkdir(parents=True, exist_ok=True)
        for filename in (
            "metrics.json",
            "report.md",
            "cmc.png",
            "retrieval_examples.png",
            "similarities.npz",
            "retrievals.json",
        ):
            shutil.copy2(evaluation / filename, target / filename)
        public_report = target / "report.md"
        public_report.write_text(
            public_report.read_text().replace(
                "![Retrieval examples](retrieval_examples.png)",
                "Face-image examples are retained locally and can be inspected in the Streamlit demo; "
                "they are excluded from this public repository.",
            )
        )
        if (directory / "history.json").exists():
            shutil.copy2(directory / "history.json", target / "history.json")
    aggregated = {}
    for k in (1, 5, 10):
        values = [
            summaries[name]["overall"]["metrics"][f"rank_{k}"]["accuracy"]
            for name in ("matcher", "matcher_seed43", "matcher_seed44")
        ]
        aggregated[f"rank_{k}"] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values, ddof=1)),
            "values": values,
        }
    primary = np.array(summaries["matcher"]["overall"]["ranks"]) <= 1
    baseline = np.array(summaries["baseline"]["overall"]["ranks"]) <= 1
    delta = primary.astype(float) - baseline.astype(float)
    rng = np.random.default_rng(42)
    intervals = np.quantile(
        delta[rng.integers(0, len(delta), (10000, len(delta)))].mean(1), [0.025, 0.975]
    )
    write_json(
        ROOT / "outputs/results/summary.json",
        {
            "dataset": manifest["dataset"],
            "counts": manifest["counts"],
            "runs": summaries,
            "three_seed_summary": aggregated,
            "paired_rank1_difference": {
                "estimate": float(delta.mean()),
                "ci95": intervals.tolist(),
                "method": "10000 paired query-identity bootstrap resamples",
                "seed": 42,
            },
        },
    )
    shutil.copy2(ROOT / "data/provenance.json", ROOT / "outputs/data_provenance.json")
    shutil.copy2(ROOT / "data/manifest.json", ROOT / "outputs/manifest.json")
    print(json.dumps(aggregated, indent=2), flush=True)


if __name__ == "__main__":
    main()
