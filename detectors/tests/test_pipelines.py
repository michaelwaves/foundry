import json
from pathlib import Path

import numpy as np
import pandas as pd

from detectors.pipelines.cache import build_feature_cache, load_feature_cache
from detectors.pipelines.fit import run_fit
from detectors.pipelines.score import run_score
from detectors.pipelines.screen import run_screen


def _base_config(synthetic_dataset, out_dir: Path, **overrides):
    config = {
        "activations_path": synthetic_dataset["activations_path"],
        "labels_path": synthetic_dataset["labels_path"],
        "hook_name": "block8",
        "extractor": {"kind": "identity", "feature_dim": synthetic_dataset["activation_dim"]},
        "pooling": "last_step",
        "out_dir": str(out_dir),
    }
    config.update(overrides)
    return config


def test_cache_round_trip(synthetic_dataset, tmp_path):
    cache_path = tmp_path / "features.npz"
    build_feature_cache(_base_config(synthetic_dataset, tmp_path), cache_path)
    cache = load_feature_cache(cache_path)
    n_designs = synthetic_dataset["n_designs"]
    n_samples = synthetic_dataset["n_samples"]
    assert cache.features.shape == (n_designs * n_samples, synthetic_dataset["activation_dim"])
    assert len(cache.design_ids) == n_designs * n_samples


def test_score_ranks_planted_feature_first(synthetic_dataset, tmp_path):
    config = _base_config(synthetic_dataset, tmp_path, scorer="auroc", aggregation="mean")
    run_score(config)
    scores = pd.read_parquet(tmp_path / "feature_scores.parquet")
    assert int(scores.iloc[0]["feature_id"]) == 3


def test_fit_then_screen_predicts_labels(synthetic_dataset, tmp_path):
    fit_dir = tmp_path / "bundle"
    fit_config = _base_config(synthetic_dataset, fit_dir, classifier="logistic", aggregation="mean")
    run_fit(fit_config)
    assert (fit_dir / "detector" / "detector.pt").exists()
    assert (fit_dir / "metrics.json").exists()

    screen_dir = tmp_path / "report"
    screen_config = {
        "bundle_path": str(fit_dir),
        "activations_path": synthetic_dataset["activations_path"],
        "out_dir": str(screen_dir),
    }
    run_screen(screen_config)
    report = pd.read_csv(screen_dir / "screen_report.csv")
    labels = pd.read_csv(synthetic_dataset["labels_path"]).set_index("design_id")["label"]
    accuracy = (report.set_index("design_id")["prediction"] == labels).mean()
    assert accuracy >= 0.75
