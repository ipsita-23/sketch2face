"""Caption a real browser recording and produce local/public demo copies.

Requires ffmpeg on PATH and Pillow (included in the documents extra).
The cuts and image masks describe the 1440x1000 recording made on 2026-11-09.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
# Real UI footage, with pauses shortened. No inference results are replaced.
SCENES = [
    (
        0,
        4,
        "Sketch2Face | Sketch-to-photo search",
        "Upload a sketch and search a gallery of candidate face photos.",
    ),
    (10, 17, "1. Choose your sketch", "Use Try a sample, or upload a JPG, PNG or BMP face sketch."),
    (
        19,
        25,
        "2. Search the built-in gallery",
        "This demo searches 37 held-out CUHK candidate photos.",
    ),
    (
        29,
        37,
        "3. Review the ranked matches",
        "The correct sample photo is rank 1; cosine similarity is 0.8373.",
    ),
    (
        40,
        47,
        "4. Upload a sketch from your files",
        "The same sketch is now uploaded through the website's file input.",
    ),
    (
        49,
        56,
        "5. Switch to My own photos",
        "Choose the candidate photos you want the model to search.",
    ),
    (
        61,
        68,
        "6. Upload your candidate gallery",
        "Five candidate photos are supplied through the gallery file input.",
    ),
    (
        70,
        81,
        "7. Compare your gallery",
        "The trained model returns a top candidate and four ranked alternatives.",
    ),
    (
        84,
        91,
        "8. Export the results as JSON",
        "Similarity is not identity probability. The correct photo must be in the gallery.",
    ),
]


def font(size: int):
    for name in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def run(args):
    subprocess.run(args, check=True)


def build(recording: Path, output: Path, public: bool, work: Path):
    filters = []
    inputs = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(recording)]
    offset = 0
    for i, (start, end, title, detail) in enumerate(SCENES):
        filters.append(f"[0:v]fps=24,trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]")
        card = Image.new("RGB", (1440, 120), "#153f37")
        draw = ImageDraw.Draw(card)
        draw.text((32, 14), title, font=font(27), fill="white")
        draw.text((32, 56), detail, font=font(21), fill="#e1eee4")
        if public:
            draw.text(
                (32, 91),
                "Public copy: CUFS image regions hidden; actual model scores and rankings preserved.",
                font=font(16),
                fill="#bbd1c4",
            )
        path = work / f"caption-{i}.png"
        card.save(path)
        inputs += ["-i", str(path)]
        offset += end - start
    filters.append(
        "".join(f"[v{i}]" for i in range(len(SCENES)))
        + f"concat=n={len(SCENES)}:v=1:a=0,setsar=1,pad=1440:1120:0:0:color=0x153f37[base]"
    )
    previous = "base"
    offset = 0
    for i, (start, end, _, _) in enumerate(SCENES):
        duration = end - start
        label = f"c{i}"
        filters.append(
            f"[{previous}][{i + 1}:v]overlay=0:1000:enable='gte(t,{offset})*lt(t,{offset + duration})'[{label}]"
        )
        previous = label
        offset += duration
    if public:
        # Opaque masks ensure public frames don't redistribute dataset face images.
        masks = [
            (130, 120, 366, 252),
            (585, 145, 174, 266),
            (578, 430, 725, 168),
            (128, 650, 187, 80),
            (128, 760, 187, 50),
        ]
        for i, (x, y, w, h) in enumerate(masks):
            label = f"m{i}"
            filters.append(
                f"[{previous}]drawbox=x={x}:y={y}:w={w}:h={h}:color=0xd6dfd7:t=fill:enable='gte(t,4)'[{label}]"
            )
            previous = label
    graph = work / ("public.ffgraph" if public else "local.ffgraph")
    graph.write_text(";\n".join(filters))
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        inputs
        + [
            "-filter_complex",
            graph.read_text(),
            "-map",
            f"[{previous}]",
            "-an",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/demo/sketch2face-demo.mp4")
    parser.add_argument(
        "--local-output", type=Path, help="Optional full image copy; keep it under ignored tmp/."
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        build(args.recording, args.output, True, work)
        if args.local_output:
            build(args.recording, args.local_output, False, work)


if __name__ == "__main__":
    main()
