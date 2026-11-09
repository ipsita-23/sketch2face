# Experimental and evaluation protocol

## Scope

The public mirror contains 188 verified CUHK identities with one viewed sketch and one cropped photo each. Full CUFS is described as CUHK 188 + AR 123 + XM2VTS 295 = 606. The latter two sources are absent as paired photos in this archive. Extra unpaired sketches are excluded.

Provenance is in `outputs/data_provenance.json`; the frozen manifest is in `outputs/manifest.json`. Results must be described as **CUFS CUHK subset results**, never as full-CUFS or forensic deployment performance.

## Splits and experiments

Split seed 42 yields 114 training, 37 validation, and 37 test identities. Each person contributes both modalities to exactly one split. Fractions are 60/20/20 with floor rounding for validation and test. This is a custom split, not a published standard protocol.

Training seeds 42, 43, and 44 use the same split; seed 42 is the primary run. One ablation disables adapters. A frozen pretrained baseline uses the same preprocessing and gallery. The matrix and selection rule are recorded in `outputs/experiment_protocol.json` before repeated runs and test evaluations.

Checkpoints maximize validation rank-1, then validation MRR; exact ties retain the earlier epoch. No model is chosen from test performance. Every predeclared run is reported, including poorer runs. Training seeds measure optimization variability, not independent dataset samples. Seeded MPS runs are not guaranteed bitwise reproducible across hardware or library versions.

## Rank-k and CMC

For each query q, r(q) is the correct photo's position among all held-out photos. Rank-k is the fraction with r(q) ≤ k. CMC plots this fraction for every k. Mean reciprocal rank averages 1/r(q).

All 37 test photos form the gallery for all 37 test sketches. Every tied distractor counts ahead of the correct candidate. If k exceeds gallery size, rank-k is unavailable rather than clipped to trivial 100%.

This is closed-set retrieval. It does not implement unknown-person rejection or calibrated identity confidence. Open-set evaluation requires separate negative identities and a validation-selected rejection rule.

## Uncertainty

Each 95% interval is a percentile bootstrap over query identities, using 2,000 resamples and seed 42. It is conditional on this gallery, split, and checkpoint. It does not capture gallery composition or training variability.

Training seeds are summarized with mean and sample standard deviation. The primary-minus-baseline rank-1 difference uses 10,000 paired bootstrap resamples of the same query identities. This preserves corresponding successes/failures. An interval crossing zero would not support a clear improvement on this test set.

Per-source metrics restrict both queries and gallery to a source. Only CUHK is available here, so these equal pooled results. If more sources are added, source gallery sizes and difficulty differ.

## Limits

- Only 37 test queries: one success changes accuracy by about 2.70 percentage points.
- Viewed artist sketches differ from eyewitness and composite forensic sketches.
- Full-CUFS, unseen-source, large-gallery, and open-set performance remain unmeasured.
- Pretraining provenance is recorded, but possible identity overlap is not independently audited.
- Demographic parity and forensic reliability are not established by aggregate accuracy.
- No novelty or state-of-the-art claim is made; comparisons apply only under this protocol.
