#!/usr/bin/env python3
"""Stratified k-fold split of a labels.csv.

Within each (label, source-prefix) stratum, rows are shuffled and round-robin
assigned to folds — so each fold's test set is class- and source-balanced.
Every example appears in test exactly once; train is the union of the other
folds. Random seed is fixed for reproducibility.

Outputs (in --out-dir):
  labels_fold0_train.csv   labels_fold0_test.csv
  ...
  labels_foldK-1_train.csv labels_foldK-1_test.csv

Usage:
  python split_labels.py \
      --labels tutorials/classifiers/rfd3_safeprotein/labels.csv \
      --out-dir tutorials/classifiers/rfd3_safeprotein \
      --n-folds 5
"""
import argparse
import random
from pathlib import Path

import pandas as pd


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.labels)
    strata = (df["label"].astype(str) + "|" + df["source_id"].apply(_source_prefix)).tolist()
    fold_test_indices = _stratified_kfold(strata, args.n_folds, args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_indices = set(range(len(df)))
    for fold, test_idx in enumerate(fold_test_indices):
        train_idx = sorted(all_indices - set(test_idx))
        train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]
        train_df.to_csv(out_dir / f"labels_fold{fold}_train.csv", index=False)
        test_df.to_csv(out_dir / f"labels_fold{fold}_test.csv", index=False)
        print(f"fold{fold}: train={len(train_df)} ({_class_dist(train_df)})  "
              f"test={len(test_df)} ({_class_dist(test_df)})")


def _stratified_kfold(strata: list[str], n_folds: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    by_stratum: dict[str, list[int]] = {}
    for index, key in enumerate(strata):
        by_stratum.setdefault(key, []).append(index)
    fold_test_indices: list[list[int]] = [[] for _ in range(n_folds)]
    for indices in by_stratum.values():
        rng.shuffle(indices)
        for offset, idx in enumerate(indices):
            fold_test_indices[offset % n_folds].append(idx)
    return [sorted(test) for test in fold_test_indices]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def _source_prefix(source_id: str) -> str:
    return source_id.split("_", 1)[0] if "_" in source_id else source_id


def _class_dist(df: pd.DataFrame) -> str:
    counts = df["label"].value_counts().to_dict()
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


if __name__ == "__main__":
    main()
