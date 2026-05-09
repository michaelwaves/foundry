#!/usr/bin/env python3
"""Trivial baseline: classify hazard vs benign from sequence length alone.

If this gets a non-trivial AUROC, the dataset has a length confound that any
"impressive" downstream classifier is partly riding on.

Usage:
  python length_baseline.py
"""
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from detectors.scorers.auroc import auroc_vectorized

ROOT = Path(__file__).parent.parent.parent

CELLS = [
    {
        "name": "rfd3_safeprotein",
        "labels_train": ROOT / "tutorials/classifiers/rfd3_safeprotein/labels_train.csv",
        "labels_test":  ROOT / "tutorials/classifiers/rfd3_safeprotein/labels_test.csv",
        "h5":   ROOT / "tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5",
        "test_h5": None,
        "hook": "block12",
    },
    {
        "name": "rf3_toxinpred3",
        "labels_train": ROOT / "tutorials/classifiers/rf3_toxinpred3/labels_train.csv",
        "labels_test":  ROOT / "tutorials/classifiers/rf3_toxinpred3/labels_test.csv",
        "h5":   ROOT / "tutorials/sae_data_rf3/train_activations/activations/activations.h5",
        "test_h5": ROOT / "tutorials/sae_data_rf3/test_activations/activations/activations.h5",
        "hook": "block12",
    },
]


def main() -> None:
    for cell in CELLS:
        train_df = _build(cell["labels_train"], cell["h5"], cell["hook"])
        test_h5 = cell["test_h5"] or cell["h5"]
        test_df = _build(cell["labels_test"], test_h5, cell["hook"])
        _report(cell["name"], train_df, test_df)


def _build(labels_path: Path, h5_path: Path, hook: str) -> pd.DataFrame:
    labels = pd.read_csv(labels_path).set_index("design_id")["label"]
    rows = []
    with h5py.File(h5_path, "r") as f:
        for design_id in f[hook].keys():
            if design_id not in labels.index:
                continue
            step0 = next(iter(f[hook][design_id]))
            arr = f[hook][design_id][step0]
            n_tokens = arr.shape[-2]                 # (... n_tokens, dim) or (n_tokens, dim)
            rows.append({"design_id": design_id, "length": int(n_tokens), "label": int(labels[design_id])})
    return pd.DataFrame(rows)


def _report(name: str, train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    n_pos_tr, n_neg_tr = (train_df.label == 1).sum(), (train_df.label == 0).sum()
    n_pos_te, n_neg_te = (test_df.label == 1).sum(), (test_df.label == 0).sum()

    pos_lens = train_df[train_df.label == 1].length
    neg_lens = train_df[train_df.label == 0].length

    test_lengths = test_df["length"].to_numpy().reshape(-1, 1).astype(np.float32)
    test_labels = test_df["label"].to_numpy()
    auroc = float(auroc_vectorized(test_lengths, test_labels)[0])
    if auroc < 0.5:                       # negative direction is also discriminative
        auroc = 1.0 - auroc

    print(f"=== {name} ===")
    print(f"  train: {len(train_df)} ({n_pos_tr} pos / {n_neg_tr} neg)")
    print(f"  test:  {len(test_df)} ({n_pos_te} pos / {n_neg_te} neg)")
    print(f"  positive length: mean={pos_lens.mean():.1f}, median={pos_lens.median():.0f}, range=[{pos_lens.min()}, {pos_lens.max()}]")
    print(f"  negative length: mean={neg_lens.mean():.1f}, median={neg_lens.median():.0f}, range=[{neg_lens.min()}, {neg_lens.max()}]")
    print(f"  ** length-only test AUROC (best direction): {auroc:.3f} **")
    print()


if __name__ == "__main__":
    main()
