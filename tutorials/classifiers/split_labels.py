#!/usr/bin/env python3
"""Split a labels.csv into train/test stratified on (label, source-prefix).

Both outputs reference the same activations.h5 — detect fit reads the train
file, detect evaluate reads the test file. Random seed is fixed so the split
is reproducible.

Usage:
  python split_labels.py \
      --labels tutorials/classifiers/rfd3_safeprotein/labels.csv \
      --train tutorials/classifiers/rfd3_safeprotein/labels_train.csv \
      --test  tutorials/classifiers/rfd3_safeprotein/labels_test.csv \
      --test-fraction 0.2
"""
import argparse
import random
from pathlib import Path

import pandas as pd


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.labels)
    strata = df["label"].astype(str) + "|" + df["source_id"].apply(_source_prefix)
    train_idx, test_idx = _stratified_split(strata.tolist(), args.test_fraction, args.seed)
    train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]
    Path(args.train).parent.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(args.train, index=False)
    test_df.to_csv(args.test, index=False)
    print(f"train: {len(train_df)} ({_class_dist(train_df)}) -> {args.train}")
    print(f"test:  {len(test_df)} ({_class_dist(test_df)}) -> {args.test}")


def _stratified_split(strata: list[str], test_fraction: float, seed: int) -> tuple[list[int], list[int]]:
    rng = random.Random(seed)
    by_stratum: dict[str, list[int]] = {}
    for index, key in enumerate(strata):
        by_stratum.setdefault(key, []).append(index)
    train_idx: list[int] = []
    test_idx: list[int] = []
    for indices in by_stratum.values():
        rng.shuffle(indices)
        cut = max(1, round(len(indices) * test_fraction)) if len(indices) > 1 else 0
        test_idx.extend(indices[:cut])
        train_idx.extend(indices[cut:])
    train_idx.sort()
    test_idx.sort()
    return train_idx, test_idx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def _source_prefix(source_id: str) -> str:
    return source_id.split("_", 1)[0] if "_" in source_id else source_id


def _class_dist(df: pd.DataFrame) -> str:
    counts = df["label"].value_counts().to_dict()
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


if __name__ == "__main__":
    main()
