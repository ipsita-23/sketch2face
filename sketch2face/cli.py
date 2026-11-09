"""Command-line entry point. Run `sketch2face --help`."""

import argparse
import json
from pathlib import Path

from .data import EXTENSIONS, discover, load_manifest, open_image, prepare, read_mapping
from .engine import choose_device, evaluate, rank_images, train, write_json
from .model import load_checkpoint


def main():
    parser = argparse.ArgumentParser(description="Sketch2Face cross-modal retrieval")
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Audit pairs and freeze identity-disjoint splits")
    inputs = prep.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--root", type=Path)
    inputs.add_argument("--input-csv", type=Path)
    prep.add_argument("--output", type=Path, default=Path("data/manifest.json"))
    prep.add_argument("--seed", type=int, default=42)
    prep.add_argument("--dataset-label", default="CUFS")
    prep.add_argument("--val-fraction", type=float, default=0.2)
    prep.add_argument("--test-fraction", type=float, default=0.2)
    for command in ("train", "baseline"):
        sub = commands.add_parser(
            command, help="Train matcher" if command == "train" else "Save frozen baseline"
        )
        sub.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
        sub.add_argument("--output", type=Path, required=True)
        sub.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
        sub.add_argument("--batch-size", type=int, default=32)
        sub.add_argument("--size", type=int, default=224)
        sub.add_argument("--seed", type=int, default=42)
        sub.add_argument(
            "--no-pretrained", action="store_true", help="Random initialization; smoke tests only"
        )
        if command == "train":
            sub.add_argument("--epochs", type=int, default=20)
            sub.add_argument("--warmup-epochs", type=int, default=3)
            sub.add_argument("--lr", type=float, default=0.0003)
            sub.add_argument("--temperature", type=float, default=0.07)
            sub.add_argument("--embedding-dim", type=int, default=256)
            sub.add_argument(
                "--shared-input", action="store_true", help="Ablation: disable modality adapters"
            )
    ev = commands.add_parser("evaluate", help="Evaluate a frozen checkpoint on held-out identities")
    ev.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    ev.add_argument("--checkpoint", type=Path, required=True)
    ev.add_argument("--output", type=Path, required=True)
    ev.add_argument("--split", choices=["val", "test"], default="test")
    ev.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    ev.add_argument("--batch-size", type=int, default=32)
    match = commands.add_parser("match", help="Rank a photo directory for one sketch")
    match.add_argument("--checkpoint", type=Path, required=True)
    match.add_argument("--sketch", type=Path, required=True)
    match.add_argument("--gallery", type=Path, required=True)
    match.add_argument("--output", type=Path, default=Path("runs/matches.json"))
    match.add_argument("--top-k", type=int, default=10)
    match.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            rows = discover(args.root) if args.root else read_mapping(args.input_csv)
            result = prepare(
                rows,
                args.output,
                args.seed,
                args.val_fraction,
                args.test_fraction,
                args.dataset_label,
            )
            print(
                json.dumps(
                    {"counts": result["counts"], "fingerprint": result["fingerprint"]}, indent=2
                )
            )
        elif args.command in ("train", "baseline"):
            options = vars(args).copy()
            for key in ("command", "manifest", "no_pretrained", "shared_input"):
                options.pop(key, None)
            options.update(
                pretrained=not args.no_pretrained,
                adapters=not getattr(args, "shared_input", False),
                baseline=args.command == "baseline",
            )
            print(train(load_manifest(args.manifest), **options))
        elif args.command == "evaluate":
            result = evaluate(
                load_manifest(args.manifest),
                args.checkpoint,
                args.output,
                args.split,
                args.device,
                args.batch_size,
            )
            print(json.dumps(result["overall"]["metrics"], indent=2))
        else:
            if args.top_k < 1:
                raise ValueError("top-k must be positive.")
            device = choose_device(args.device)
            model, payload = load_checkpoint(args.checkpoint, device)
            files = sorted(
                path for path in args.gallery.iterdir() if path.suffix.lower() in EXTENSIONS
            )
            ranking = rank_images(
                model,
                open_image(args.sketch),
                [open_image(p) for p in files],
                device,
                payload["config"]["size"],
            )
            result = [
                {"rank": i + 1, "photo": str(files[j]), "similarity": score}
                for i, (j, score) in enumerate(ranking[: args.top_k])
            ]
            write_json(args.output, result)
            print(json.dumps(result, indent=2))
    except (ValueError, FileNotFoundError, KeyError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
