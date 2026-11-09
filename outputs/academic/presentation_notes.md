## Slide 1 - Sketch2Face

Introduce the project as sketch-to-photo retrieval. Replace the two marked placeholders before submission. All numeric results come from completed local experiments.

## Slide 2 - Problem and objective

This is a retrieval project, not a face generation project. Training identities differ from test identities. Motivation is forensic search, but the evaluation uses viewed artist sketches.

## Slide 3 - Dataset audit

Sources: references [1], [2], [6]. Official archive returned HTTP 500. Public mirror version 1 has 188 files in photos and 188 files in sketches. Archive checksum and mapping rules are in outputs/data_provenance.json.

## Slide 4 - Identity-disjoint evaluation

Split seed 42, one pair per identity, custom 60/20/20 split with floor rounding. Both images of each person stay in the same split. The correct photo is present by design: this is closed-set evaluation.

## Slide 5 - Model architecture

ResNet-18: He et al. [3]. The adapters are residual 1x1 convolutions, zero-initialized. There are only 18 adapter parameters total. No face detector, landmark alignment, photo synthesis, or language model is used.

## Slide 6 - Paired contrastive learning

The diagonal pair indices are the cross-entropy targets. S and P are L2-normalized embeddings. The symmetric paired objective follows the form used in CLIP [4]; no CLIP weights or text encoder are used. Similarity is not an identity probability.

## Slide 7 - Training and comparisons

Learning rates: 3e-4 projection/adapters and 3e-5 encoder; weight decay 1e-4. Frozen BatchNorm statistics. Checkpoint selection uses validation rank-1, then MRR. Primary seed fixed at 42. Test never selects the model. AdamW: [5].

## Slide 8 - Measured retrieval accuracy

All values are percentages on the same 37-photo test gallery. Epoch is selected using validation. Source: outputs/results/summary.json. All predeclared runs are included.

## Slide 9 - CMC comparison

Source: actual CMC arrays in per-run metrics.json. CMC is the fraction of correct photos found by rank k. The primary model reaches 100 percent at rank 10 within this gallery; this does not predict accuracy on larger galleries.

## Slide 10 - Rank-k comparison

Editable native PowerPoint chart. Source: outputs/results/summary.json. The primary model has higher rank-1, while the no-adapter ablation has higher rank-5. Both reach 100 percent rank-10 on these observed queries.

## Slide 11 - What the experiments show

The gain interval uses 10000 paired query bootstrap samples. The ± quantity is sample standard deviation across three training seeds, not a confidence interval. The primary model recovers 19 baseline failures and loses two baseline successes.

## Slide 12 - Adapter ablation and errors

Source: summary.json and matcher/retrievals.json. Do not claim that the adapters explain all improvement. The safer finding is the benefit of the trained representation relative to generic frozen features. Demonstrate actual failures in the local app instead of embedding dataset photos in the public deck.

## Slide 13 - Learning curves

Source: runs/matcher/history.json copied into outputs/results/matcher/history.json. The dashed line separates warmup and layer-4 fine-tuning. The selected primary epoch is 20, at the training budget boundary, so optimal duration and convergence are not established.

## Slide 14 - Limitations

Each test success changes accuracy by 2.70 percentage points. Bootstrap intervals condition on this fixed gallery. A 100 percent observed rank-10 result is not proof of perfect future retrieval. Pretraining identity overlap was not independently audited.

## Slide 15 - Demo and conclusion

The demo uses the exact evaluation preprocessing and model loader. In upload mode the user supplies candidate photos; the system cannot know whether the person is present. Scores are similarities only. Dataset and weights remain local; code, metrics, and documentation are reproducible from the public repository.

## Slide 16 - References

Full citations and access URLs:
[1] X. Wang and X. Tang, "Face Photo-Sketch Synthesis and Recognition," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 31, no. 11, pp. 1955-1967, 2009. doi:10.1109/TPAMI.2008.222.
[2] W. Zhang, X. Wang, and X. Tang, "Coupled Information-Theoretic Encoding for Face Photo-Sketch Recognition," IEEE CVPR, pp. 513-520, 2011.
[3] K. He, X. Zhang, S. Ren, and J. Sun, "Deep Residual Learning for Image Recognition," IEEE CVPR, pp. 770-778, 2016. https://arxiv.org/abs/1512.03385.
[4] A. Radford et al., "Learning Transferable Visual Models From Natural Language Supervision," ICML, PMLR 139, pp. 8748-8763, 2021. https://arxiv.org/abs/2103.00020.
[5] I. Loshchilov and F. Hutter, "Decoupled Weight Decay Regularization," ICLR, 2019. https://arxiv.org/abs/1711.05101.
[6] Arbaz Khan, "CUHK Face Sketch Database (CUFS)," Kaggle public mirror, version 1, updated October 8, 2020; accessed November 9, 2026. https://www.kaggle.com/datasets/arbazkhan971/cuhk-face-sketch-database-cufs. Data rights retained by original authors.
