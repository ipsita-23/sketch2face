"""Validated pairing and immutable identity-disjoint dataset manifests."""

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import torch
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms as T

EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".pgm"}
SPLITS = ("train", "val", "test")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def open_image(path):
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def image_transform(train=False, size=224):
    # Both modalities become grayscale RGB: no shortcut through photo color.
    operations = [T.Grayscale(num_output_channels=3), T.Resize((size, size))]
    if train:
        operations += [T.RandomAffine(degrees=5, translate=(0.025, 0.025), fill=255)]
    return T.Compose(
        operations + [T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]
    )


def discover(root):
    """Read canonical source/{sketches,photos}/IDENTITY.ext folders; never guess pairs."""
    root = Path(root).resolve()
    rows = []
    for source_dir in sorted(root.iterdir()):
        if not source_dir.is_dir():
            continue
        sketches, photos = source_dir / "sketches", source_dir / "photos"
        if not sketches.is_dir() or not photos.is_dir():
            continue

        def index(folder):
            result = {}
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in EXTENSIONS:
                    if path.stem in result:
                        raise ValueError(f"Ambiguous identity stem in {folder}: {path.stem}")
                    result[path.stem] = path
            return result

        sk, ph = index(sketches), index(photos)
        if sk.keys() != ph.keys():
            raise ValueError(
                f"Unpaired files in {source_dir}: "
                f"sketch-only={sorted(sk.keys() - ph.keys())[:10]}, "
                f"photo-only={sorted(ph.keys() - sk.keys())[:10]}"
            )
        for identity in sorted(sk):
            rows.append(
                {
                    "identity": identity,
                    "source": source_dir.name,
                    "sketch": str(sk[identity]),
                    "photo": str(ph[identity]),
                }
            )
    if not rows:
        raise ValueError(
            "No pairs found. Use SOURCE/sketches/ID.ext and SOURCE/photos/ID.ext "
            "or supply --input-csv with explicit mappings."
        )
    return rows


def read_mapping(path):
    path = Path(path).resolve()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"identity", "source", "sketch", "photo"} <= set(reader.fieldnames or []):
            raise ValueError("CSV needs identity,source,sketch,photo columns.")
        rows = []
        for item in reader:
            row = {key: item[key].strip() for key in ("identity", "source", "sketch", "photo")}
            for key in ("sketch", "photo"):
                row[key] = str((path.parent / row[key]).resolve())
            rows.append(row)
    return rows


def prepare(rows, output, seed=42, val_fraction=0.2, test_fraction=0.2, label="CUFS"):
    if not 0 < val_fraction < 1 or not 0 < test_fraction < 1 or val_fraction + test_fraction >= 1:
        raise ValueError("Validation and test fractions must be positive and sum to less than 1.")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError(f"Refusing to replace a frozen manifest: {output}. Choose a new path.")
    seen_ids, seen_pixels = set(), {}
    groups = defaultdict(list)
    for raw in rows:
        row = dict(raw)
        if not row.get("identity") or not row.get("source"):
            raise ValueError("Identity and source cannot be empty.")
        # Identity labels must be consistent within a source; prefix separates source namespaces.
        uid = f"{row['source']}:{row['identity']}"
        if uid in seen_ids:
            raise ValueError(f"Multiple pairs for identity {uid}; this protocol expects one pair.")
        seen_ids.add(uid)
        row["uid"] = uid
        for modality in ("sketch", "photo"):
            path = Path(row[modality]).resolve()
            image = open_image(path)
            if min(image.size) < 32:
                raise ValueError(f"Image is too small: {path}")
            pixel_hash = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
            if pixel_hash in seen_pixels:
                raise ValueError(f"Duplicate image pixels: {path} and {seen_pixels[pixel_hash]}")
            seen_pixels[pixel_hash] = str(path)
            row[modality] = str(path)
            row[f"{modality}_sha256"] = file_hash(path)
        groups[row["source"]].append(row)
    if not groups:
        raise ValueError("Dataset has no pairs.")
    rng = random.Random(seed)
    result = []
    for source, members in sorted(groups.items()):
        if len(members) < 5:
            raise ValueError(f"Source {source} needs at least five identities for three splits.")
        members.sort(key=lambda item: item["uid"])
        rng.shuffle(members)
        nval = max(1, int(len(members) * val_fraction))
        ntest = max(1, int(len(members) * test_fraction))
        if len(members) - nval - ntest < 2:
            raise ValueError(f"Source {source} leaves fewer than two training identities.")
        for index, row in enumerate(members):
            row["split"] = "val" if index < nval else "test" if index < nval + ntest else "train"
            result.append(row)
    result.sort(key=lambda item: item["uid"])
    manifest = {
        "schema_version": 1,
        "dataset": label,
        "seed": seed,
        "fractions": {"val": val_fraction, "test": test_fraction},
        "fingerprint": fingerprint(result),
        "rows": result,
        "counts": dict(Counter(row["split"] for row in result)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_manifest(path, verify=True):
    manifest = json.loads(Path(path).read_text())
    rows = manifest["rows"]
    if fingerprint(rows) != manifest["fingerprint"]:
        raise ValueError("Manifest fingerprint mismatch; regenerate and retrain after changes.")
    if len({row["uid"] for row in rows}) != len(rows):
        raise ValueError("Identity repeats across manifest rows.")
    if any(row["split"] not in SPLITS for row in rows):
        raise ValueError("Unknown split in manifest.")
    if verify:
        for row in rows:
            for key in ("sketch", "photo"):
                if file_hash(row[key]) != row[f"{key}_sha256"]:
                    raise ValueError(f"Image changed since preparation: {row[key]}")
    return manifest


class Pairs(Dataset):
    def __init__(self, rows, train=False, size=224):
        self.rows = rows
        self.train = train
        self.transform = image_transform(train, size)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        images = [open_image(row[key]) for key in ("sketch", "photo")]
        if self.transform is not None:
            # Paired horizontal flips preserve correspondence; affine jitter is independent.
            if self.train and torch.rand(()) < 0.5:
                images = [ImageOps.mirror(image) for image in images]
            images = [self.transform(image) for image in images]
        return images[0], images[1]
