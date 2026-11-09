"""Publication figures from measured experiment outputs, never invented measurements."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/figures"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = json.loads((ROOT / "outputs/results/summary.json").read_text())
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
        }
    )
    colors = ["#7b8794", "#087f8c", "#c27a29"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for name, label, color in zip(
        ["baseline", "matcher", "shared_input"],
        ["Frozen baseline", "Trained matcher (seed 42)", "Without adapters"],
        colors,
    ):
        cmc = summary["runs"][name]["overall"]["cmc"]
        ax.plot(range(1, len(cmc) + 1), np.array(cmc) * 100, label=label, color=color, lw=2.2)
    ax.set(xlabel="Rank k", ylabel="Retrieval accuracy (%)", ylim=(0, 103), xlim=(1, 37))
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(OUT / "cmc_comparison.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(3)
    for offset, name, label, color in zip(
        [-0.25, 0, 0.25],
        ["baseline", "matcher", "shared_input"],
        ["Frozen baseline", "Trained matcher", "Without adapters"],
        colors,
    ):
        values = [summary["runs"][name]["overall"]["metrics"][f"rank_{k}"] for k in (1, 5, 10)]
        y = np.array([v["accuracy"] * 100 for v in values])
        intervals = np.array([v["ci95"] for v in values]).T * 100
        ax.bar(
            x + offset,
            y,
            width=0.23,
            label=label,
            color=color,
            yerr=np.stack([y - intervals[0], intervals[1] - y]),
            capsize=3,
        )
    ax.set(
        xticks=x, xticklabels=["Rank-1", "Rank-5", "Rank-10"], ylabel="Accuracy (%)", ylim=(0, 115)
    )
    ax.legend(frameon=False, ncols=3, loc="upper center", fontsize=8)
    ax.grid(axis="y", alpha=0.15)
    fig.tight_layout()
    fig.savefig(OUT / "rank_comparison.png", dpi=200)
    plt.close(fig)

    history = json.loads((ROOT / "runs/matcher/history.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))
    epochs = [row["epoch"] for row in history]
    axes[0].plot(epochs, [r["loss"] for r in history], color="#087f8c", lw=2)
    axes[0].set(xlabel="Epoch", ylabel="Training contrastive loss")
    axes[1].plot(epochs, [r["val_rank1"] * 100 for r in history], color="#c27a29", lw=2)
    axes[1].set(xlabel="Epoch", ylabel="Validation rank-1 (%)", ylim=(0, 100))
    for ax in axes:
        ax.axvline(3.5, color="#7b8794", ls="--", lw=1)
        ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(OUT / "learning_curves.png", dpi=200)
    plt.close(fig)

    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    rows = [row for row in manifest["rows"] if row["split"] == "test"][:4]
    fig, axes = plt.subplots(1, 8, figsize=(10, 2.6))
    for i, row in enumerate(rows):
        for j, key in enumerate(("sketch", "photo")):
            axes[2 * i + j].imshow(Image.open(row[key]).convert("RGB"))
            axes[2 * i + j].set_title(key.capitalize(), fontsize=9)
            axes[2 * i + j].axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "dataset_pairs.png", dpi=180)
    plt.close(fig)
    import shutil

    shutil.copy2(ROOT / "outputs/results/matcher/retrieval_examples.png", OUT / "hard_queries.png")

    cases = json.loads((ROOT / "outputs/results/matcher/retrievals.json").read_text())
    cases = sorted(cases, key=lambda row: row["correct_rank"])
    example = next(case for case in cases if case["correct_rank"] == 1)
    fig, axes = plt.subplots(1, 6, figsize=(10, 2.7))
    for i, (ax, item) in enumerate(
        zip(axes, [{"photo": example["sketch"], "identity": "Query"}] + example["top"][:5])
    ):
        ax.imshow(Image.open(item["photo"]).convert("RGB"))
        ax.set_title(
            "Query sketch" if i == 0 else f"Rank {i}" + (" (correct)" if i == 1 else ""),
            fontsize=10,
        )
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "successful_retrieval.png", dpi=180)
    plt.close(fig)
    print(f"Saved measured-result figures to {OUT}")


if __name__ == "__main__":
    main()
