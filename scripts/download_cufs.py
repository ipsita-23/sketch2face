"""Download and audit the public mirror; extract only its verified CUHK subset.

Usage: python scripts/download_cufs.py
The mirror's 606-pair description does not match its actual contents.
"""

import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sketch2face.data import prepare

REF = "arbazkhan971/cuhk-face-sketch-database-cufs"
URL = "https://www.kaggle.com/api/v1/datasets/download/" + REF


def main():
    downloads = ROOT / "data/downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / "cufs-kaggle.zip"
    if not archive.exists():
        temporary = archive.with_suffix(".part")
        print("Downloading public CUFS mirror...", flush=True)
        urllib.request.urlretrieve(URL, temporary)
        temporary.rename(archive)
    metadata_url = "https://www.kaggle.com/api/v1/datasets/view/" + REF
    metadata = json.load(urllib.request.urlopen(metadata_url, timeout=30))
    (downloads / "metadata.json").write_text(json.dumps(metadata, indent=2))
    rows = []
    with zipfile.ZipFile(archive) as bundle:
        photos = {
            PurePosixPath(n).stem.lower(): n
            for n in bundle.namelist()
            if n.startswith("photos/") and n.lower().endswith(".jpg")
        }
        sketches = {}
        for name in bundle.namelist():
            if not name.startswith("sketches/") or not name.lower().endswith(".jpg"):
                continue
            # The mirror uses F2-/M2- for the f-/m- photo group, and -sz1 for sketch artist.
            identity = re.sub(r"-sz\d+$", "", PurePosixPath(name).stem.lower())
            identity = re.sub(r"^([fm])2-", r"\1-", identity)
            if identity in sketches:
                raise ValueError(f"Ambiguous sketch identity: {identity}")
            sketches[identity] = name
        if photos.keys() != sketches.keys() or len(photos) != 188:
            raise ValueError(
                "Mirror contents changed: expected exactly 188 unambiguous CUHK pairs."
            )
        for identity in sorted(photos):
            row = {"identity": identity, "source": "CUHK"}
            for key, mapping in [("photo", photos), ("sketch", sketches)]:
                target = (
                    ROOT
                    / "data/cufs/CUHK"
                    / ("photos" if key == "photo" else "sketches")
                    / f"{identity}.jpg"
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(mapping[identity]))
                row[key] = str(target)
            rows.append(row)
        from collections import Counter

        counts = dict(Counter(n.split("/")[0] for n in bundle.namelist()))
    provenance = {
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "url": URL,
        "metadata_url": metadata_url,
        "version": metadata.get("currentVersionNumber"),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "license": metadata.get("licenseName"),
        "extracted_pairs": 188,
        "source": "CUHK",
        "advertised_full_cufs_pairs": 606,
        "full_cufs_available": False,
        "archive_folder_counts": counts,
        "exclusions": "Original-resolution duplicate CUHK files and 1194 unpaired cropped/original sketches excluded. AR and XM2VTS photo pairs absent.",
        "identity_mapping": "Case-insensitive; remove trailing -sz1; F2-/M2- maps to f-/m-. f1-/m1- unchanged.",
        "note": "Original authors retain data rights. Public mirror availability is not a redistribution license. Research use only; do not commit or redistribute images.",
    }
    (ROOT / "data/provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    manifest_path = ROOT / "data/manifest.json"
    if not manifest_path.exists():
        manifest = prepare(rows, manifest_path, label="CUFS CUHK subset (188 identities)")
        print(json.dumps(manifest["counts"], indent=2))
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
