#!/usr/bin/env python3
"""Stratified k-fold split of a labels.csv.

Two split modes:
  * Default: stratified by (label, source-prefix); rows shuffled then round-robin
    assigned to folds within each stratum.
  * --clusters CLUSTERS.csv: cluster-aware. All rows sharing a cluster_id land
    in the same fold (no homology leak across train/test). Class balance per
    fold is best-effort (greedy by smallest current count of dominant label).

Outputs (in --out-dir, with optional --tag suffix):
  labels_fold0_train[_<tag>].csv   labels_fold0_test[_<tag>].csv
  ...
  labels_foldK-1_train[_<tag>].csv labels_foldK-1_test[_<tag>].csv

Usage:
  # random (paralog leakage)
  python split_labels.py --labels rfd3_safeprotein/labels.csv \\
      --out-dir rfd3_safeprotein --n-folds 5

  # cluster-aware (homology-clean)
  python split_labels.py --labels rfd3_safeprotein/labels.csv \\
      --clusters rfd3_safeprotein/clusters.csv \\
      --out-dir rfd3_safeprotein --tag cluster --n-folds 5
"""
import argparse
import os
import random
from collections import defaultdict
from pathlib import Path

import pandas as pd


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.labels)
    if args.clusters:
        clusters = pd.read_csv(args.clusters).set_index("design_id")["cluster_id"]
        groups = [clusters.get(d, d) for d in df["design_id"]]
        fold_test_indices = _grouped_kfold(df["label"].astype(str).tolist(),
                                           groups, args.n_folds, args.seed)
        mode = f"cluster-aware ({clusters.nunique()} clusters)"
    else:
        strata = (df["label"].astype(str) + "|" + df["source_id"].apply(_source_prefix)).tolist()
        fold_test_indices = _stratified_kfold(strata, args.n_folds, args.seed)
        mode = "random stratified"

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.tag}" if args.tag else ""
    print(f"[{mode}] tag={args.tag or '<none>'}  n_folds={args.n_folds}")
    all_indices = set(range(len(df)))
    for fold, test_idx in enumerate(fold_test_indices):
        train_idx = sorted(all_indices - set(test_idx))
        train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]
        train_df.to_csv(out_dir / f"labels_fold{fold}_train{suffix}.csv", index=False)
        test_df.to_csv(out_dir / f"labels_fold{fold}_test{suffix}.csv", index=False)
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


def _grouped_kfold(labels: list[str], groups: list, n_folds: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    by_group: dict = defaultdict(lambda: {"indices": [], "labels": []})
    for i, (label, group) in enumerate(zip(labels, groups)):
        by_group[group]["indices"].append(i)
        by_group[group]["labels"].append(label)
    ordered = sorted(by_group.items(), key=lambda kv: -len(kv[1]["indices"]))
    rng.shuffle(ordered)
    ordered.sort(key=lambda kv: -len(kv[1]["indices"]))     # stable: large first
    fold_label_counts: list[dict] = [defaultdict(int) for _ in range(n_folds)]
    fold_test_indices: list[list[int]] = [[] for _ in range(n_folds)]
    for _, info in ordered:
        dominant = max(set(info["labels"]), key=info["labels"].count)
        best = min(range(n_folds),
                   key=lambda k: (fold_label_counts[k][dominant], len(fold_test_indices[k])))
        for label, idx in zip(info["labels"], info["indices"]):
            fold_label_counts[best][label] += 1
            fold_test_indices[best].append(idx)
    return [sorted(test) for test in fold_test_indices]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--clusters", default=None,
                        help="CSV with design_id,cluster_id from cluster_sequences.py")
    parser.add_argument("--tag", default=os.environ.get("CLASSIFIER_RUN_TAG", ""),
                        help="suffix for output filenames; matches CLASSIFIER_RUN_TAG")
    return parser.parse_args()


def _source_prefix(source_id: str) -> str:
    return source_id.split("_", 1)[0] if "_" in source_id else source_id


def _class_dist(df: pd.DataFrame) -> str:
    counts = df["label"].value_counts().to_dict()
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


if __name__ == "__main__":
    main()
