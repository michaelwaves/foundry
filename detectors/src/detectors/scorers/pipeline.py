import numpy as np
import pandas as pd

from detectors.scorers.base import Scorer


def score_all_features(
    matrix: np.ndarray,
    feature_ids: np.ndarray,
    target: np.ndarray,
    scorer: Scorer,
    p_value_top_k: int = 200,
) -> pd.DataFrame:
    n_samples = (matrix > 0).sum(axis=0).astype(int)
    is_constant = matrix.max(axis=0) == matrix.min(axis=0)

    scores = scorer.score_all(matrix, target).astype(float)
    scores[is_constant] = scorer.null_value
    p_values = _compute_top_k_p_values(matrix, target, scores, scorer, is_constant, p_value_top_k)

    df = pd.DataFrame({
        "feature_id": feature_ids.astype(int),
        scorer.score_column: scores,
        scorer.p_value_column: p_values,
        "n_samples": n_samples,
    })
    return df.sort_values(
        scorer.score_column,
        ascending=False,
        key=lambda s: np.abs(s - scorer.null_value),
    ).reset_index(drop=True)


def _compute_top_k_p_values(
    matrix: np.ndarray,
    target: np.ndarray,
    scores: np.ndarray,
    scorer: Scorer,
    is_constant: np.ndarray,
    top_k: int,
) -> np.ndarray:
    p_values = np.ones_like(scores)
    candidate_count = min(top_k, len(scores))
    distance_from_null = np.abs(scores - scorer.null_value)
    top_indices = np.argpartition(distance_from_null, -candidate_count)[-candidate_count:]
    for index in top_indices:
        if not is_constant[index]:
            p_values[index] = scorer.compute_p_value(matrix[:, index], target)
    return p_values
