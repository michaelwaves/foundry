import json
from pathlib import Path

import numpy as np
import pandas as pd

from detectors.classifiers import DETECTORS
from detectors.io.artifacts import save_bundle
from detectors.pipelines.cache import build_extractor, build_feature_cache
from detectors.pipelines.labeled import aggregate_per_design, attach_labels
from detectors.scorers.auroc import auroc_vectorized


def run_fit(config: dict) -> None:
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    cache = build_feature_cache(config, out_dir / "features.npz")
    cache, row_labels = attach_labels(cache, config["labels_path"])
    matrix, labels, design_ids = aggregate_per_design(
        cache, config.get("aggregation", "mean"), row_labels,
    )
    matrix, selected_indices = _select_top_k(matrix, labels, config.get("select_top_k"))

    detector_cls = DETECTORS[config.get("classifier", "logistic")]
    detector = detector_cls(**config.get("classifier_kwargs", {}))
    detector.fit(matrix, labels)

    extractor = build_extractor(config["extractor"])
    save_bundle(out_dir, extractor, detector, _persistable_config(config, selected_indices))
    _save_metrics(out_dir, detector, matrix, labels, design_ids)


def _select_top_k(matrix: np.ndarray, labels: np.ndarray, top_k: int | None) -> tuple[np.ndarray, np.ndarray | None]:
    if top_k is None:
        return matrix, None
    scores = auroc_vectorized(matrix, labels)
    order = np.argsort(-np.abs(scores - 0.5))[: int(top_k)]
    return matrix[:, order], order


def _persistable_config(config: dict, selected_indices: np.ndarray | None) -> dict:
    snapshot = {k: v for k, v in config.items() if k != "out_dir"}
    if selected_indices is not None:
        snapshot["selected_feature_indices"] = selected_indices.tolist()
    return snapshot


def _save_metrics(out_dir: Path, detector, matrix: np.ndarray, labels: np.ndarray, design_ids: np.ndarray) -> None:
    probabilities = detector.predict_proba(matrix)
    predictions = probabilities.argmax(axis=1)
    accuracy = float((predictions == labels).mean())
    train_auroc = float(auroc_vectorized(probabilities[:, 1:2], labels)[0])
    metrics = {"train_accuracy": accuracy, "train_auroc": train_auroc, "n_designs": int(len(labels))}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    pd.DataFrame({"design_id": design_ids, "label": labels,
                  "probability": probabilities[:, 1]}).to_csv(out_dir / "train_predictions.csv", index=False)
