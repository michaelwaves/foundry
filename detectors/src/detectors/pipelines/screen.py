from pathlib import Path

import numpy as np
import pandas as pd

from detectors.io.artifacts import load_bundle
from detectors.pipelines.cache import build_feature_cache
from detectors.pipelines.labeled import _aggregate


def run_screen(config: dict) -> pd.DataFrame:
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = load_bundle(Path(config["bundle_path"]))

    cache_config = dict(bundle.config)
    cache_config["activations_path"] = config["activations_path"]
    cache = build_feature_cache(cache_config, out_dir / "features.npz")

    matrix, design_ids = _aggregate_per_design_unlabeled(cache, bundle.config.get("aggregation", "mean"))
    selected = bundle.config.get("selected_feature_indices")
    if selected is not None:
        matrix = matrix[:, np.array(selected, dtype=np.int64)]

    probabilities = bundle.detector.predict_proba(matrix)
    report = pd.DataFrame({
        "design_id": design_ids,
        "probability": probabilities[:, 1],
        "prediction": probabilities.argmax(axis=1),
    })
    report.to_csv(out_dir / "screen_report.csv", index=False)
    return report


def _aggregate_per_design_unlabeled(cache, aggregation: str) -> tuple[np.ndarray, np.ndarray]:
    unique_design_ids, inverse = np.unique(cache.design_ids, return_inverse=True)
    matrix = np.zeros((len(unique_design_ids), cache.features.shape[1]), dtype=np.float32)
    for design_index in range(len(unique_design_ids)):
        matrix[design_index] = _aggregate(cache.features[inverse == design_index], aggregation)
    return matrix, unique_design_ids
