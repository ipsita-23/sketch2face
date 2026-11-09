"""Closed-set CMC with pessimistic ties and identity-bootstrap intervals."""

import numpy as np


def retrieval_metrics(
    similarities, query_ids, gallery_ids, ks=(1, 5, 10), seed=42, bootstraps=2000
):
    scores = np.asarray(similarities, dtype=np.float64)
    if scores.shape != (len(query_ids), len(gallery_ids)) or not scores.size:
        raise ValueError("Scores must be a nonempty queries-by-gallery matrix.")
    if not np.isfinite(scores).all():
        raise ValueError("Non-finite retrieval scores.")
    if len(set(query_ids)) != len(query_ids) or len(set(gallery_ids)) != len(gallery_ids):
        raise ValueError("This protocol requires one query and one gallery image per identity.")
    if not set(query_ids) <= set(gallery_ids):
        raise ValueError("Every query must have a correct gallery photo (closed-set protocol).")
    lookup = {identity: i for i, identity in enumerate(gallery_ids)}
    correct = np.array([lookup[identity] for identity in query_ids])
    # Every tied distractor counts ahead of the correct match, avoiding optimistic tie accuracy.
    ranks = (scores >= scores[np.arange(len(query_ids)), correct, None]).sum(axis=1)
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(ranks), size=(bootstraps, len(ranks)))
    metrics = {}
    for k in ks:
        if k < 1:
            raise ValueError("Ranks must be positive.")
        if k > len(gallery_ids):
            metrics[f"rank_{k}"] = None
            continue
        hits = ranks <= k
        interval = np.quantile(hits[samples].mean(axis=1), [0.025, 0.975])
        metrics[f"rank_{k}"] = {
            "accuracy": float(hits.mean()),
            "ci95": [float(value) for value in interval],
        }
    return {
        "queries": len(query_ids),
        "gallery_size": len(gallery_ids),
        "metrics": metrics,
        "ranks": ranks.tolist(),
        "cmc": [float((ranks <= k).mean()) for k in range(1, len(gallery_ids) + 1)],
        "mean_reciprocal_rank": float((1 / ranks).mean()),
        "tie_policy": "pessimistic",
    }
