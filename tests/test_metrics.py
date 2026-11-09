import numpy as np
import pytest

from sketch2face.metrics import retrieval_metrics


def test_known_ranks_and_reordered_gallery():
    # Correct ranks are 2, 1, 3, despite a shuffled gallery order.
    scores = [[0.9, 0.8, 0.1], [0.9, 0.2, 0.1], [0.8, 0.7, 0.6]]
    result = retrieval_metrics(scores, ["a", "b", "c"], ["b", "a", "c"], ks=(1, 2, 3, 5))
    assert result["ranks"] == [2, 1, 3]
    assert result["cmc"] == [1 / 3, 2 / 3, 1]
    assert result["metrics"]["rank_5"] is None


def test_ties_do_not_inflate_accuracy():
    result = retrieval_metrics(np.ones((3, 3)), list("abc"), list("abc"))
    assert result["ranks"] == [3, 3, 3]
    assert result["metrics"]["rank_1"]["accuracy"] == 0


def test_reject_missing_matches_and_nonfinite_scores():
    with pytest.raises(ValueError, match="correct gallery"):
        retrieval_metrics([[1]], ["a"], ["b"])
    with pytest.raises(ValueError, match="Non-finite"):
        retrieval_metrics([[np.nan]], ["a"], ["a"])


def test_bootstrap_reproducible():
    matrix = [[1, 0], [1, 0]]
    assert retrieval_metrics(matrix, ["a", "b"], ["a", "b"]) == retrieval_metrics(
        matrix, ["a", "b"], ["a", "b"]
    )
