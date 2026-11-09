"""Training, evaluation, and inference with recorded experimental provenance."""

import json
import platform
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data import Pairs, file_hash, image_transform, open_image
from .metrics import retrieval_metrics
from .model import Matcher, contrastive_loss, load_checkpoint


def choose_device(name="auto"):
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(min(4, torch.get_num_threads()))


def write_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


@torch.inference_mode()
def embed_pairs(model, rows, device, batch_size=32, size=224):
    model.eval()
    sketches, photos = [], []
    loader = DataLoader(Pairs(rows, size=size), batch_size=batch_size, shuffle=False)
    for sk, ph in loader:
        sketches.append(model(sk.to(device), "sketch").cpu())
        photos.append(model(ph.to(device), "photo").cpu())
    if not sketches:
        raise ValueError("Selected split has no images.")
    return torch.cat(sketches).numpy(), torch.cat(photos).numpy()


def score_pairs(model, rows, device, batch_size=32, size=224, seed=42):
    sk, ph = embed_pairs(model, rows, device, batch_size, size)
    scores = sk @ ph.T
    ids = [row["uid"] for row in rows]
    return retrieval_metrics(scores, ids, ids, seed=seed), scores


def checkpoint_payload(model, manifest, config, epoch, validation):
    return {
        "schema_version": 1,
        "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
        "model_config": model.config,
        "manifest_fingerprint": manifest["fingerprint"],
        "dataset": manifest["dataset"],
        "config": config,
        "epoch": epoch,
        "validation": validation,
        "pretraining": "torchvision ResNet18 IMAGENET1K_V1" if config["pretrained"] else "none",
        "environment": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "platform": platform.platform(),
        },
    }


def train(
    manifest,
    output,
    *,
    epochs=20,
    warmup_epochs=3,
    batch_size=32,
    lr=0.0003,
    temperature=0.07,
    embedding_dim=256,
    seed=42,
    size=224,
    device="auto",
    pretrained=True,
    adapters=True,
    baseline=False,
):
    if epochs < 1 or batch_size < 2 or lr <= 0 or size < 32 or temperature <= 0:
        raise ValueError("Need epochs >= 1, batch size >= 2, positive lr/temperature, size >= 32.")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Run directory is not empty: {output}. Use a new directory.")
    output.mkdir(parents=True, exist_ok=True)
    seed_everything(seed)
    device = choose_device(device)
    config = {
        "epochs": epochs,
        "warmup_epochs": warmup_epochs,
        "batch_size": batch_size,
        "lr": lr,
        "temperature": temperature,
        "embedding_dim": embedding_dim,
        "seed": seed,
        "size": size,
        "device": str(device),
        "pretrained": pretrained,
        "adapters": adapters,
        "baseline": baseline,
    }
    write_json(output / "config.json", config)
    model = Matcher(embedding_dim, pretrained, baseline, adapters).to(device)
    train_rows = [row for row in manifest["rows"] if row["split"] == "train"]
    val_rows = [row for row in manifest["rows"] if row["split"] == "val"]
    if len(train_rows) < 2 or not val_rows:
        raise ValueError(
            "Manifest needs at least two training identities and validation identities."
        )
    if baseline:
        val, _ = score_pairs(model, val_rows, device, batch_size, size, seed)
        torch.save(checkpoint_payload(model, manifest, config, 0, val), output / "best.pt")
        return output / "best.pt"
    loader = DataLoader(
        Pairs(train_rows, train=True, size=size),
        batch_size=min(batch_size, len(train_rows)),
        shuffle=True,
        drop_last=False,
        generator=torch.Generator().manual_seed(seed),
    )
    # Frozen parameters can stay in optimizer: they receive gradients only when unfrozen.
    optimizer = torch.optim.AdamW(
        [
            {"params": model.encoder.parameters(), "lr": lr / 10},
            {"params": model.adapters.parameters(), "lr": lr},
            {"params": model.projector.parameters(), "lr": lr},
        ],
        weight_decay=0.0001,
    )
    history, best = [], (-1.0, -1.0)
    started = time.monotonic()
    for epoch in range(1, epochs + 1):
        model.training_stage(fine_tune=epoch > warmup_epochs)
        total_loss, count = 0.0, 0
        for sketches, photos in loader:
            if len(sketches) < 2:
                continue
            optimizer.zero_grad(set_to_none=True)
            sk = model(sketches.to(device), "sketch")
            ph = model(photos.to(device), "photo")
            loss = contrastive_loss(sk, ph, temperature)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite training loss; check inputs and learning rate.")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            total_loss += float(loss.detach().cpu()) * len(sketches)
            count += len(sketches)
        val, _ = score_pairs(model, val_rows, device, batch_size, size, seed)
        row = {
            "epoch": epoch,
            "loss": total_loss / count,
            "val_rank1": val["metrics"]["rank_1"]["accuracy"],
            "val_mrr": val["mean_reciprocal_rank"],
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }
        history.append(row)
        write_json(output / "history.json", history)
        print(json.dumps(row), flush=True)
        selection = (row["val_rank1"], row["val_mrr"])
        if selection > best:
            best = selection
            torch.save(checkpoint_payload(model, manifest, config, epoch, val), output / "best.pt")
    return output / "best.pt"


def evaluate(manifest, checkpoint, output, split="test", device="auto", batch_size=32):
    device = choose_device(device)
    model, payload = load_checkpoint(checkpoint, device)
    if payload["manifest_fingerprint"] != manifest["fingerprint"]:
        raise ValueError(
            "Checkpoint and manifest differ; evaluation would mix experimental splits."
        )
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Evaluation directory is not empty: {output}.")
    rows = [row for row in manifest["rows"] if row["split"] == split]
    overall, scores = score_pairs(model, rows, device, batch_size, payload["config"]["size"])
    source_results = {}
    for source in sorted({row["source"] for row in rows}):
        positions = [i for i, row in enumerate(rows) if row["source"] == source]
        ids = [rows[i]["uid"] for i in positions]
        source_results[source] = retrieval_metrics(scores[np.ix_(positions, positions)], ids, ids)
    result = {
        "dataset": manifest["dataset"],
        "split": split,
        "overall": overall,
        "per_source": source_results,
        "manifest_fingerprint": manifest["fingerprint"],
        "checkpoint_sha256": file_hash(checkpoint),
        "checkpoint": str(Path(checkpoint).resolve()),
        "model_config": payload["model_config"],
        "training_config": payload["config"],
        "selected_epoch": payload["epoch"],
        "pretraining": payload["pretraining"],
        "environment": payload["environment"],
        "bootstrap_seed": 42,
        "bootstrap_samples": 2000,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "metrics.json", result)
    np.savez_compressed(
        output / "similarities.npz",
        scores=scores,
        identities=np.array([row["uid"] for row in rows]),
    )
    order = np.argsort(-scores, axis=1, kind="stable")
    retrievals = [
        {
            "query": row["uid"],
            "sketch": row["sketch"],
            "correct_rank": overall["ranks"][i],
            "top": [
                {
                    "identity": rows[j]["uid"],
                    "photo": rows[j]["photo"],
                    "score": float(scores[i, j]),
                }
                for j in order[i, :10]
            ],
        }
        for i, row in enumerate(rows)
    ]
    write_json(output / "retrievals.json", retrievals)
    render_evaluation(output, result, retrievals)
    return result


def render_evaluation(output, result, retrievals):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(
        range(1, len(result["overall"]["cmc"]) + 1),
        np.array(result["overall"]["cmc"]) * 100,
        color="#087f8c",
        linewidth=2,
    )
    ax.set(
        xlabel="Rank k",
        ylabel="Retrieval accuracy (%)",
        ylim=(0, 101),
        title=f"{result['dataset']} — {result['split']} CMC",
    )
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output / "cmc.png", dpi=180)
    plt.close(fig)
    cases = sorted(retrievals, key=lambda row: row["correct_rank"], reverse=True)[:4]
    fig, axes = plt.subplots(len(cases), 6, figsize=(12, 2.5 * len(cases)), squeeze=False)
    for row_axes, case in zip(axes, cases):
        images = [{"photo": case["sketch"], "identity": "Sketch", "score": None}] + case["top"][:5]
        for ax in row_axes:
            ax.axis("off")
        for i, (ax, item) in enumerate(zip(row_axes, images)):
            ax.imshow(open_image(item["photo"]))
            title = case["query"] if i == 0 else f"#{i} {item['identity']}"
            ax.set_title(
                title,
                fontsize=8,
                color="#087f8c" if item["identity"] == case["query"] else "#222222",
            )
    fig.suptitle("Hardest queries: sketch and top five candidates (correct match in teal)")
    fig.tight_layout()
    fig.savefig(output / "retrieval_examples.png", dpi=140)
    plt.close(fig)
    lines = [
        f"# {result['dataset']} retrieval accuracy report",
        "",
        (
            f"Split: {result['split']}. Queries: {result['overall']['queries']}. "
            f"Gallery: {result['overall']['gallery_size']} photos."
        ),
        "",
        "| Gallery | Rank-1 | Rank-5 | Rank-10 |",
        "|---|---:|---:|---:|",
    ]

    def cell(metric):
        if metric is None:
            return "N/A (gallery < k)"
        low, high = metric["ci95"]
        return f"{metric['accuracy']:.1%} [{low:.1%}, {high:.1%}]"

    for name, group in [("Pooled", result["overall"]), *result["per_source"].items()]:
        values = [cell(group["metrics"][f"rank_{k}"]) for k in (1, 5, 10)]
        lines.append(f"| {name} (n={group['gallery_size']}) | " + " | ".join(values) + " |")
    lines += [
        "",
        "Intervals are 95% percentile bootstrap intervals over query identities (2,000 resamples).",
        "Per-source galleries contain only that source; their difficulty differs from the pooled gallery.",
        "Tied distractors count ahead of the correct photo. Closed-set: every query has one gallery match.",
        "",
        "![CMC](cmc.png)",
        "",
        "![Retrieval examples](retrieval_examples.png)",
        "",
        f"Selected epoch: {result['selected_epoch']}. Pretraining: {result['pretraining']}.",
        f"Manifest SHA-256: `{result['manifest_fingerprint']}`.",
        f"Checkpoint SHA-256: `{result['checkpoint_sha256']}`.",
        "",
        "CUFS uses viewed artist sketches. These measurements do not validate eyewitness or composite sketches.",
        "External pretraining overlap is not independently audited; scores are similarities, not identity probabilities.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")


@torch.inference_mode()
def rank_images(model, sketch, photos, device, size=224, batch_size=32):
    if not photos:
        raise ValueError("Provide at least one gallery photo.")
    model.eval()
    transform = image_transform(size=size)
    query = model(transform(sketch).unsqueeze(0).to(device), "sketch").cpu()
    embeddings = []
    for start in range(0, len(photos), batch_size):
        batch = torch.stack([transform(image) for image in photos[start : start + batch_size]])
        embeddings.append(model(batch.to(device), "photo").cpu())
    scores = (query @ torch.cat(embeddings).T).numpy()[0]
    return [(int(index), float(scores[index])) for index in np.argsort(-scores, kind="stable")]
