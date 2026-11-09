# Website demo video

[Watch or download the demo MP4](sketch2face-demo.mp4).

The 64-second, captioned screen recording shows the real local website and trained model. It has no audio. Captions explain each step, so it can also be used during a project presentation.

| Time | What happens |
|---|---|
| 00:00 | Website introduction |
| 00:04 | Select a sample sketch |
| 00:11 | Search the built-in 37-photo gallery |
| 00:17 | Review the correct sample photo at rank 1, with cosine similarity 0.8373 |
| 00:25 | Upload a sketch file |
| 00:32 | Switch to a custom photo gallery |
| 00:39 | Supply five candidate photo files |
| 00:46 | Review the custom-gallery shortlist |
| 00:57 | Export the results as JSON |

The public repository video covers the dataset image regions because the project does not redistribute CUFS face images. The actual model scores, candidate labels, and ranking are preserved. The full local recording, with visible sketches and photos, is at `tmp/demo/sketch2face-demo-full.mp4` in the original project workspace. That local file is ignored by Git and is not included in a fresh clone.

This is a demonstration of one query, not an accuracy measurement. Benchmark results come from all 37 held-out queries; see the main README and `outputs/results/`. The correct person's photo must be in the candidate gallery. Similarity scores are not identity probabilities.

## Recording and editing

Recorded on 9 November 2026 at a 1440 × 1000 browser viewport using the actual website at `http://localhost:8000`. The browser file inputs were populated through browser automation; the operating system's file chooser is not shown. Idle time was shortened, and captions were added. No returned candidates or scores were changed.

To rebuild from the original raw recording with the same scene timing:

```bash
uv sync --extra documents
uv run python scripts/build_demo_video.py /absolute/path/to/raw-recording.mp4 \
  --local-output tmp/demo/sketch2face-demo-full.mp4
```

Install FFmpeg separately and ensure `ffmpeg` is on PATH. The script uses Pillow to create captions and FFmpeg to cut and encode H.264 MP4 with fast-start playback. Scene timings and public image masks are specific to this recording; update them for a new capture and inspect the output before publishing. Keep recordings containing dataset images under ignored `tmp/` unless you have redistribution permission.
