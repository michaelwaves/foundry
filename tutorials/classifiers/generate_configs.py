#!/usr/bin/env python3
"""Emit detect score/fit/evaluate yaml configs for the full sweep.

One source-of-truth datasets dict declares each labelled cell (activations.h5,
labels CSVs, SAE checkpoints per hook, raw activation_dim per hook). The
generator stamps out yaml configs for every (hook x extractor) combination so
that adding a hook or a new label set is a one-entry edit.

Outputs:
  configs/<dataset>/score_<hook>_<extractor>.yaml
  configs/<dataset>/fit_<hook>_<extractor>.yaml
  configs/<dataset>/eval_<hook>_<extractor>.yaml

Usage:
  python generate_configs.py
"""
import os
from pathlib import Path

import yaml


HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUTPUT_ROOT = ROOT / "outputs" / "classifiers"
DEVICE = os.environ.get("CLASSIFIER_DEVICE", "cuda:0")

DATASETS = {
    "rfd3_safeprotein": {
        "model": "rfd3",
        "activations": ROOT / "tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5",
        "labels": HERE / "rfd3_safeprotein/labels.csv",
        "labels_train": HERE / "rfd3_safeprotein/labels_train.csv",
        "labels_test": HERE / "rfd3_safeprotein/labels_test.csv",
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
        "labels": HERE / "rf3_toxinpred3/labels.csv",
        "labels_train": HERE / "rf3_toxinpred3/labels_train.csv",
        "labels_test": HERE / "rf3_toxinpred3/labels_test.csv",
        "test_activations": ROOT / "tutorials/sae_data_rf3/test_activations/activations/activations.h5",
        "sae_root": ROOT / "outputs/sae/2026-04-26_15-23-45/train",
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
                _emit_fit(dataset_name, dataset, hook_name, hook_spec, extractor)
                _emit_eval(dataset_name, dataset, hook_name, extractor)
    print("done")


def _emit_score(name: str, dataset: dict, hook: str, hook_spec: dict, extractor: str) -> None:
    config = {
        "activations_path": str(dataset["activations"]),
        "labels_path": str(dataset["labels"]),
        "hook_name": hook,
        "extractor": _extractor_block(dataset, hook, hook_spec, extractor),
        "pooling": "last_step",
        "scorer": "auroc",
        "aggregation": "mean",
        "top_k": 50,
        "p_value_top_k": 200,
    }
    _write(f"configs/{name}/score_{hook}_{extractor}.yaml", config)


def _emit_fit(name: str, dataset: dict, hook: str, hook_spec: dict, extractor: str) -> None:
    config = {
        "activations_path": str(dataset["activations"]),
        "labels_path": str(dataset["labels_train"]),
        "hook_name": hook,
        "extractor": _extractor_block(dataset, hook, hook_spec, extractor),
        "pooling": "last_step",
        "aggregation": "mean",
        "classifier": "logistic",
        "classifier_kwargs": {"epochs": 300, "lr": 0.05, "weight_decay": 1.0e-4},
    }
    if extractor == "sae_encode":
        config["select_top_k"] = 50
    _write(f"configs/{name}/fit_{hook}_{extractor}.yaml", config)


def _emit_eval(name: str, dataset: dict, hook: str, extractor: str) -> None:
    test_activations = dataset.get("test_activations") or dataset["activations"]
    config = {
        "bundle_path": str(OUTPUT_ROOT / name / "fit" / f"{dataset['model']}_{hook}_{extractor}"),
        "activations_path": str(test_activations),
        "labels_path": str(dataset["labels_test"]),
    }
    _write(f"configs/{name}/eval_{hook}_{extractor}.yaml", config)


def _extractor_block(dataset: dict, hook: str, hook_spec: dict, extractor: str) -> dict:
    if extractor == "identity":
        return {"kind": "identity", "feature_dim": hook_spec["activation_dim"]}
    return {
        "kind": "sae_encode",
        "checkpoint_path": str(dataset["sae_root"] / hook / "final.pt"),
        "device": DEVICE,
    }


def _write(rel_path: str, config: dict) -> None:
    path = HERE / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False))


if __name__ == "__main__":
    main()
