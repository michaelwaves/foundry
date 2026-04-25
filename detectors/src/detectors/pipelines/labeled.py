import numpy as np
import pandas as pd

from detectors.pipelines.cache import FeatureCache


def attach_labels(cache: FeatureCache, labels_path: str) -> np.ndarray:
    labels_df = pd.read_csv(labels_path).set_index("design_id")
    return np.array([int(labels_df.loc[design_id, "label"]) for design_id in cache.design_ids])


def aggregate_per_design(
    cache: FeatureCache,
    aggregation: str,
    row_labels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pool multiple samples per design into one feature row + label."""
    unique_design_ids, inverse = np.unique(cache.design_ids, return_inverse=True)
    n_designs, n_features = len(unique_design_ids), cache.features.shape[1]
    matrix = np.zeros((n_designs, n_features), dtype=np.float32)
    labels = np.zeros(n_designs, dtype=np.int64)
    for design_index, design_id in enumerate(unique_design_ids):
        rows = cache.features[inverse == design_index]
        matrix[design_index] = _aggregate(rows, aggregation)
        labels[design_index] = row_labels[np.where(inverse == design_index)[0][0]]
    return matrix, labels, unique_design_ids


def _aggregate(rows: np.ndarray, aggregation: str) -> np.ndarray:
    if aggregation == "mean":
        return rows.mean(axis=0)
    if aggregation == "max":
        return rows.max(axis=0)
    if aggregation == "sum":
        return rows.sum(axis=0)
    raise ValueError(f"unknown aggregation: {aggregation}")
