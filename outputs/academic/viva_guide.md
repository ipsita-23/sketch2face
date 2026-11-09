# Sketch2Face viva guide

## What does the project do?

Given a face sketch, it ranks candidate photos by similarity to the same identity.

## Why is this cross-modal?

The query is a drawing and the gallery contains photographs; their appearance statistics differ.

## Is it a photo generator?

No. It learns vectors for retrieval, without generating face photos.

## Why use pretrained ResNet-18?

The small paired dataset is insufficient to train a strong visual backbone from scratch. ImageNet features provide a starting representation.

## What are embeddings?

Numerical feature vectors. Here trained outputs have 256 dimensions and unit length.

## What is the loss?

Average of sketch-to-photo and photo-to-sketch cross-entropy over batch cosine similarities, with matched pairs on the diagonal.

## How is leakage avoided?

Split identities before augmentation; keep each sketch and photo together; verify file hashes and require checkpoint-manifest agreement.

## What exactly was tested?

188 CUHK identities split 114/37/37. Each test sketch retrieves from all 37 held-out photos. This is a custom subset protocol.

## Why not say full CUFS?

The downloaded mirror lacks paired AR and XM2VTS photos. Its 606-pair listing does not match its actual usable contents.

## What did we find?

Primary rank-1 is 72.97%, baseline 27.03%; the three-seed matcher mean is 69.37% ± 3.12 percentage points.

## What is rank-5?

The fraction of queries whose correct photograph is anywhere in the first five results.

## Do adapters always improve retrieval?

No. In one controlled seed they improve rank-1 but have lower rank-5. More ablation seeds are needed.

## Does 100% rank-10 prove perfect identification?

No. It describes only 37 observed queries in a small closed-set gallery; all correct photos are present.

## Are scores probabilities?

No. They are cosine similarities and are not calibrated identity confidence.

## Can this be deployed by police?

These experiments do not establish forensic reliability. Eyewitness, composite, open-set, and demographic tests are missing.

## What is original about this work?

The project integrates established methods in an audited, reproducible pipeline and evaluates them locally. It does not claim a novel algorithm.

## What should improve next?

Obtain full CUFS through its owners, enlarge galleries, evaluate unseen sources and forensic sketches, repeat ablations, and consider alignment and feature caching.
