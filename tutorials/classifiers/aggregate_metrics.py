#!/usr/bin/env python3
"""Aggregate sweep outputs into two markdown tables.

  Q1 (probing):    one row per (dataset, model, hook, extractor), with mean
                   and std of train + eval metrics across CV folds.
  Q2 (attribution): one row per top SAE feature per (dataset, model, hook),
                   pulled from feature_scores.parquet.

Per-fold rows are also written to probes_per_fold.csv for inspection.

Usage:
  python aggregate_metrics.py --sweep-root outputs/classifiers --out tutorials/classifiers/results
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


GROUP_COLS = ("dataset", "model", "hook", "extractor")


def main() -> None:
    args = _parse_args()
    sweep_root = Path(args.sweep_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_fold = _collect_probes(sweep_root)
    if not per_fold.empty:
        per_fold.to_csv(out_dir / "probes_per_fold.csv", index=False)
        agg = _aggregate_folds(per_fold)
        agg.to_csv(out_dir / "probes.csv", index=False)
        (out_dir / "probes.md").write_text(_to_markdown(agg))
        print(f"probe rows: {len(agg)} (from {len(per_fold)} fold runs) -> {out_dir/'probes.md'}")

    attr_table = _collect_top_features(sweep_root, args.top_k)
    if not attr_table.empty:
        attr_table.to_csv(out_dir / "top_features.csv", index=False)
        (out_dir / "top_features.md").write_text(_to_markdown(attr_table))
        print(f"top-feature rows: {len(attr_table)} -> {out_dir/'top_features.md'}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep-root", required=True,
                        help="root dir containing <dataset>/{score,fit,eval}/<cell>/...")
    parser.add_argument("--out", required=True)
    parser.add_argument("--top-k", type=int, default=20,
                        help="rows per (dataset, hook) in the attribution table")
    return parser.parse_args()


def _collect_probes(sweep_root: Path) -> pd.DataFrame:
    rows = []
    for fit_metrics in sorted(sweep_root.glob("*/fit/*/metrics.json")):
        cell = _parse_cell(fit_metrics)
        cell["fit_metrics"] = _load_json(fit_metrics)
        eval_path = sweep_root / cell["dataset"] / "eval" / cell["cell_name"] / "eval_metrics.json"
        cell["eval_metrics"] = _load_json(eval_path) if eval_path.exists() else {}
        rows.append(_flatten_probe_row(cell))
    return pd.DataFrame(rows)


def _aggregate_folds(per_fold: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [c for c in per_fold.columns
                   if c not in (*GROUP_COLS, "fold", "cell_name")
                   and pd.api.types.is_numeric_dtype(per_fold[c])]
    rows = []
    for keys, group in per_fold.groupby(list(GROUP_COLS), dropna=False):
        row = dict(zip(GROUP_COLS, keys))
        row["n_folds"] = len(group)
        for col in metric_cols:
            values = group[col].dropna().to_numpy()
            if values.size == 0:
                continue
            row[f"{col}_mean"] = float(np.mean(values))
            row[f"{col}_std"] = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
        rows.append(row)
    columns = list(GROUP_COLS) + ["n_folds"] + sorted(
        c for c in {k for r in rows for k in r} if c not in (*GROUP_COLS, "n_folds")
    )
    return pd.DataFrame(rows, columns=columns)


def _collect_top_features(sweep_root: Path, top_k: int) -> pd.DataFrame:
    rows = []
    for parquet in sorted(sweep_root.glob("*/score/*/feature_scores.parquet")):
        cell = _parse_cell(parquet)
        scores = pd.read_parquet(parquet).head(top_k)
        for _, feat in scores.iterrows():
            rows.append({
                "dataset": cell["dataset"],
                "model": cell["model"],
                "hook": cell["hook"],
                "extractor": cell["extractor"],
                "feature_id": int(feat["feature_id"]),
                "auroc": float(feat["auroc"]),
                "auroc_p": float(feat["auroc_p"]),
                "q_value": float(feat["q_value"]),
                "n_samples": int(feat["n_samples"]),
            })
    return pd.DataFrame(rows)


def _parse_cell(path: Path) -> dict:
    cell_dir = path.parent
    dataset = cell_dir.parent.parent.name
    raw_name = cell_dir.name
    fold = None
    base_name = raw_name
    if "__fold" in raw_name:
        base_name, fold_str = raw_name.split("__fold", 1)
        fold = int(fold_str)
    parts = base_name.split("_")
    model, hook, extractor = parts[0], parts[1], "_".join(parts[2:])
    return {"dataset": dataset, "cell_name": raw_name,
            "model": model, "hook": hook, "extractor": extractor, "fold": fold}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _flatten_probe_row(cell: dict) -> dict:
    row = {k: cell[k] for k in (*GROUP_COLS, "fold", "cell_name")}
    for prefix, metrics in (("train", cell["fit_metrics"]), ("eval", cell["eval_metrics"])):
        for key, value in metrics.items():
            row[f"{prefix}_{key}"] = value
    return row


def _to_markdown(df: pd.DataFrame) -> str:
    rows = [
        "| " + " | ".join(df.columns) + " |",
        "|" + "|".join(["---"] * len(df.columns)) + "|",
    ]
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(_fmt(v) for v in row) + " |")
    return "\n".join(rows) + "\n"


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.4f}"
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return str(v)


if __name__ == "__main__":
    main()
