import numpy as np
from scipy.stats import mannwhitneyu, rankdata


def auroc_vectorized(matrix: np.ndarray, target: np.ndarray) -> np.ndarray:
    y = target.astype(bool)
    n_pos, n_neg = int(y.sum()), int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return np.full(matrix.shape[1], 0.5)
    ranks = rankdata(matrix, axis=0, method="average")
    u_statistic = ranks[y].sum(axis=0) - n_pos * (n_pos + 1) / 2.0
    return u_statistic / (n_pos * n_neg)


def auroc_p_value(activations: np.ndarray, target: np.ndarray) -> float:
    y = target.astype(bool)
    pos, neg = activations[y], activations[~y]
    if pos.size == 0 or neg.size == 0:
        return 1.0
    return float(mannwhitneyu(pos, neg, alternative="two-sided").pvalue)
