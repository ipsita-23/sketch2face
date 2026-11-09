import numpy as np
import pytest
from PIL import Image

from sketch2face.data import load_manifest, prepare


def pairs(tmp_path, n=10):
    rows = []
    rng = np.random.default_rng(8)
    for i in range(n):
        row = {"identity": str(i), "source": "test-source"}
        for key in ("sketch", "photo"):
            path = tmp_path / f"{i}-{key}.png"
            Image.fromarray(rng.integers(0, 256, (40, 40, 3), dtype=np.uint8)).save(path)
            row[key] = str(path)
        rows.append(row)
    return rows


def test_split_is_disjoint_and_reproducible(tmp_path):
    rows = pairs(tmp_path)
    first = prepare(rows, tmp_path / "first.json")
    second = prepare(list(reversed(rows)), tmp_path / "second.json")
    assert first["fingerprint"] == second["fingerprint"]
    assert first["counts"] == {"train": 6, "val": 2, "test": 2}
    assert len({row["uid"] for row in first["rows"]}) == 10
    assert load_manifest(tmp_path / "first.json") == first


def test_reject_duplicate_pixels_and_changed_files(tmp_path):
    rows = pairs(tmp_path)
    rows[1]["photo"] = rows[0]["photo"]
    with pytest.raises(ValueError, match="Duplicate"):
        prepare(rows, tmp_path / "bad.json")
    rows = pairs(tmp_path)
    prepare(rows, tmp_path / "good.json")
    Image.new("RGB", (40, 40)).save(rows[0]["sketch"])
    with pytest.raises(ValueError, match="changed"):
        load_manifest(tmp_path / "good.json")


def test_manifest_is_not_silently_overwritten(tmp_path):
    rows = pairs(tmp_path)
    prepare(rows, tmp_path / "frozen.json")
    with pytest.raises(ValueError, match="Refusing"):
        prepare(rows, tmp_path / "frozen.json")
