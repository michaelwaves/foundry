import numpy as np
import pytest

from detectors.scorers import SCORERS
from detectors.scorers.auroc import auroc_p_value, auroc_vectorized
from detectors.scorers.pipeline import score_all_features


def test_auroc_perfect_separation():
    matrix = np.array([[0.0], [0.0], [1.0], [1.0]])
    target = np.array([0, 0, 1, 1])
    assert auroc_vectorized(matrix, target)[0] == pytest.approx(1.0)


def test_auroc_inverted_separation():
    matrix = np.array([[1.0], [1.0], [0.0], [0.0]])
    target = np.array([0, 0, 1, 1])
    assert auroc_vectorized(matrix, target)[0] == pytest.approx(0.0)


def test_auroc_all_one_class_returns_null():
    matrix = np.random.randn(10, 3)
    assert (auroc_vectorized(matrix, np.ones(10)) == 0.5).all()
    assert (auroc_vectorized(matrix, np.zeros(10)) == 0.5).all()


def test_auroc_vectorized_matches_per_feature():
    rng = np.random.default_rng(0)
    matrix = rng.standard_normal((50, 8))
    target = rng.integers(0, 2, 50)
    fast = auroc_vectorized(matrix, target)
    slow = np.array([auroc_vectorized(matrix[:, i:i+1], target)[0] for i in range(8)])
    np.testing.assert_allclose(fast, slow)


def test_auroc_p_value_finite():
    rng = np.random.default_rng(1)
    activations = rng.standard_normal(100)
    target = rng.integers(0, 2, 100)
    assert 0.0 <= auroc_p_value(activations, target) <= 1.0


def test_score_pipeline_ranks_planted_feature_first():
    rng = np.random.default_rng(2)
    n, f = 200, 16
    target = rng.integers(0, 2, n)
    matrix = rng.standard_normal((n, f))
    matrix[:, 7] = target + 0.1 * rng.standard_normal(n)
    df = score_all_features(matrix, np.arange(f), target, SCORERS["auroc"])
    assert int(df.iloc[0]["feature_id"]) == 7


def test_score_pipeline_marks_constants_null():
    matrix = np.zeros((20, 4))
    matrix[:, 0] = 1.0
    target = np.array([0, 1] * 10)
    df = score_all_features(matrix, np.arange(4), target, SCORERS["auroc"])
    constants = df[df["feature_id"].isin([0, 1, 2, 3])]
    null = SCORERS["auroc"].null_value
    assert (constants["auroc"] == null).all()
