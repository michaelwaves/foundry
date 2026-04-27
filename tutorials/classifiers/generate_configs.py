#!/usr/bin/env python3
"""Emit detect score/fit/evaluate yaml configs for the full sweep.

One source-of-truth datasets dict declares each labelled cell (activations.h5,
labels CSV + per-fold splits, SAE checkpoints per hook, raw activation_dim per
hook). Fit/eval are emitted per fold so the sweep produces N_FOLDS bundles per
(hook x extractor); aggregate_metrics.py averages metrics across folds. Score
stays one-per-cell — it's univariate per-feature attribution against the full
labels file, no train/test split needed.

Outputs:
  configs/<dataset>/score_<hook>_<extractor>.yaml
  configs/<dataset>/fit_<hook>_<extractor>__fold<k>.yaml
  configs/<dataset>/eval_<hook>_<extractor>__fold<k>.yaml

Usage:
  python generate_configs.py
"""
import os
from pathlib import Path

import yaml


HERE = Path(__file__).parent
ROOT = HERE.parent.parent
DEVICE = os.environ.get("CLASSIFIER_DEVICE", "cuda:0")
N_FOLDS = int(os.environ.get("CLASSIFIER_N_FOLDS", "5"))
RUN_TAG = os.environ.get("CLASSIFIER_RUN_TAG", "")
# Labels tag is decoupled from the run tag — lets you e.g. run "stop_overfitting"
# experiments against the existing random labels (LABELS_TAG="") rather than
# requiring labels_*_stop_overfitting.csv files to exist. Defaults to RUN_TAG
# for backwards compatibility with the cluster-split workflow.
LABELS_TAG = os.environ.get("CLASSIFIER_LABELS_TAG", RUN_TAG)
WEIGHT_DECAY = float(os.environ.get("CLASSIFIER_WEIGHT_DECAY", "1e-4"))
EPOCHS = int(os.environ.get("CLASSIFIER_EPOCHS", "300"))
# When set, applies select_top_k to BOTH extractors. When unset, preserves the
# original asymmetric default (50 for sae_encode, none for identity).
SELECT_TOP_K_BOTH = os.environ.get("CLASSIFIER_SELECT_TOP_K")
_SUFFIX = f"_{RUN_TAG}" if RUN_TAG else ""
_LABELS_SUFFIX = f"_{LABELS_TAG}" if LABELS_TAG else ""
CONFIGS_ROOT = HERE / f"configs{_SUFFIX}"
OUTPUT_ROOT = ROOT / f"outputs/classifiers{_SUFFIX}"

DATASETS = {
    "rfd3_safeprotein": {
        "model": "rfd3",
        "activations": ROOT / "tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5",
        "labels_dir": HERE / "rfd3_safeprotein",
        "sae_root": ROOT / "outputs/sae/2026-04-26_15-38-55/train",
        "hooks": {
            "block6":  {"activation_dim": 768},
            "block8":  {"activation_dim": 768},
            "block12": {"activation_dim": 768},
        },
    },
    "rf3_toxinpred3": {
        "model": "rf3",
        "activations": ROOT / "tutorials/sae_data_rf3/train_activations/activations/activations.h5",
        "labels_dir": HERE / "rf3_toxinpred3",
        "test_activations": ROOT / "tutorials/sae_data_rf3/test_activations/activations/activations.h5",
        "sae_root": ROOT / "outputs/sae/2026-04-26_15-23-45/train",
        "hooks": {
            "block12": {"activation_dim": 768},
            "block16": {"activation_dim": 768},
        },
    },
    "rf3_safeprotein": {
        "model": "rf3",
        "activations": ROOT / "tutorials/sae_data_rf3/uniprot/train_activations/activations/activations.h5",
        "labels_dir": HERE / "rf3_safeprotein",
        "sae_root": ROOT / "outputs/sae/2026-04-26_22-03-07/train",
        "hooks": {
            "block12": {"activation_dim": 768},
            "block16": {"activation_dim": 768},
        },
    },
}

EXTRACTORS = ("identity", "sae_encode")


def main() -> None:
    for dataset_name, dataset in DATASETS.items():
        for hook_name, hook_spec in dataset["hooks"].items():
            for extractor in EXTRACTORS:
                _emit_score(dataset_name, dataset, hook_name, hook_spec, extractor)
                for fold in range(N_FOLDS):
                    _emit_fit(dataset_name, dataset, hook_name, hook_spec, extractor, fold)
                    _emit_eval(dataset_name, dataset, hook_name, extractor, fold)
    print(f"done (n_folds={N_FOLDS}, tag={RUN_TAG or '<none>'})")


def _emit_score(name: str, dataset: dict, hook: str, hook_spec: dict, extractor: str) -> None:
    config = {
        "activations_path": str(dataset["activations"]),
        "labels_path": str(dataset["labels_dir"] / "labels.csv"),
        "hook_name": hook,
        "extractor": _extractor_block(dataset, hook, hook_spec, extractor),
        "pooling": "last_step",
        "scorer": "auroc",
        "aggregation": "mean",
        "top_k": 50,
        "p_value_top_k": 200,
    }
    _write(f"{name}/score_{hook}_{extractor}.yaml", config)


def _emit_fit(name: str, dataset: dict, hook: str, hook_spec: dict,
              extractor: str, fold: int) -> None:
    config = {
        "activations_path": str(dataset["activations"]),
        "labels_path": str(dataset["labels_dir"] / f"labels_fold{fold}_train{_LABELS_SUFFIX}.csv"),
        "hook_name": hook,
        "extractor": _extractor_block(dataset, hook, hook_spec, extractor),
        "pooling": "last_step",
        "aggregation": "mean",
        "classifier": "logistic",
        "classifier_kwargs": {"epochs": EPOCHS, "lr": 0.05, "weight_decay": WEIGHT_DECAY},
    }
    if SELECT_TOP_K_BOTH is not None:
        config["select_top_k"] = int(SELECT_TOP_K_BOTH)
    elif extractor == "sae_encode":
        config["select_top_k"] = 50
    _write(f"{name}/fit_{hook}_{extractor}__fold{fold}.yaml", config)


def _emit_eval(name: str, dataset: dict, hook: str, extractor: str, fold: int) -> None:
    test_activations = dataset.get("test_activations") or dataset["activations"]
    cell = f"{dataset['model']}_{hook}_{extractor}__fold{fold}"
    config = {
        "bundle_path": str(OUTPUT_ROOT / name / "fit" / cell),
        "activations_path": str(test_activations),
        "labels_path": str(dataset["labels_dir"] / f"labels_fold{fold}_test{_LABELS_SUFFIX}.csv"),
    }
    _write(f"{name}/eval_{hook}_{extractor}__fold{fold}.yaml", config)


def _extractor_block(dataset: dict, hook: str, hook_spec: dict, extractor: str) -> dict:
    if extractor == "identity":
        return {"kind": "identity", "feature_dim": hook_spec["activation_dim"]}
    return {
        "kind": "sae_encode",
        "checkpoint_path": str(dataset["sae_root"] / hook / "final.pt"),
        "device": DEVICE,
    }


def _write(rel_path: str, config: dict) -> None:
    path = CONFIGS_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False))


if __name__ == "__main__":
    main()
