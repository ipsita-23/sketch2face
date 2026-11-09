# Architecture and implementation

## Problem definition

Given one face sketch and N candidate photographs, return the photographs ordered by cosine similarity. In closed-set evaluation, exactly one gallery photograph depicts the query identity. This is retrieval across image modalities, not classification into training identities or sketch-to-photo image generation.

The experiment uses the CUHK subset of CUFS. Training identities never appear in validation or test. Within each split there is one sketch and one photograph per identity.

## Data flow

Acquisition → explicit pairing → duplicate audit → seeded identity split → manifest with image hashes → paired training → validation checkpoint selection → held-out evaluation → rank-k report.

At inference: image → EXIF orientation correction → RGB conversion → three-channel grayscale → resize → ImageNet normalization → modality adapter → shared backbone → projection → L2 normalization. Cosine similarities with gallery embeddings determine the ranking.

The mirror images are already cropped to 200 × 250 pixels. The pipeline resizes these to 224 × 224; it does not estimate landmarks or align arbitrary uploads. Both modalities use identical grayscale conversion. Training adds a synchronized horizontal flip and independent affine jitter (±5 degrees, translation up to 2.5%); validation and inference use deterministic transforms.

## Model

Each modality has a learned 1 × 1 convolution with 3 input/output channels and no bias. Weights start at zero and the output is added to the input, initially preserving pretrained inputs. The two adapters add only 18 parameters. They cannot perform spatial alignment or reconstruct missing features.

The shared encoder is torchvision ResNet-18 with ImageNet-1K V1 weights. Global pooling produces 512 features. The head is Linear(512, 256), ReLU, Linear(256, 256). The final vector is normalized to unit length.

The baseline bypasses adapters and projection and uses normalized raw 512-dimensional pretrained features. The no-adapter ablation retains the trainable projection and identical fine-tuning schedule.

## Objective

For B distinct paired identities, S and P contain normalized sketch and photo embeddings. Logits are S Pᵀ / τ, with τ = 0.07. Correct classes are the diagonal indices. Loss averages cross-entropy in the sketch-to-photo direction and the transposed photo-to-sketch direction. Other batch identities supply negatives. A singleton final batch is skipped because it contains no negatives; other partial batches are retained.

## Optimization

AdamW uses learning rate 3e-4 for adapters/projection, 3e-5 for the backbone, weight decay 1e-4, and gradient clipping to norm 5. Epochs 1–3 freeze the encoder. Epochs 4–20 unfreeze only layer 4. BatchNorm running statistics remain frozen. The shared encoder enforces common structure while adapters permit small input corrections.

## Checkpoint integrity

Checkpoints store parameters, model/training configuration, epoch, validation metrics, dataset label, manifest fingerprint, pretraining source, and software environment. Evaluation records checkpoint SHA-256 and rejects a manifest mismatch. Loading uses PyTorch's restricted weights-only loader.

The manifest uses absolute paths and image byte hashes. Moving the dataset requires a new manifest and matching run. Source labels namespace identities. Exact pixel duplicate checks do not establish that edited images depict different people.

## Interface

Streamlit runs locally. Users choose a checkpoint and a held-out query or uploaded images. Ranking uses evaluation's preprocessing and model functions. Dataset mode shows the correct rank; upload mode has no ground truth. JSON export is available. The app does not send uploads to an external face search service.

Gallery features are recomputed per search. Large galleries could use cached embeddings keyed by checkpoint hash, preprocessing, and image hash; that is an extension rather than current performance.
