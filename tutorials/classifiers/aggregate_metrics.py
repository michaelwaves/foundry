#!/usr/bin/env python3
"""Aggregate sweep outputs into two markdown tables.

  Q1 (probing):    one row per (dataset, model, hook, extractor), columns are
                   train + eval metrics globbed from metrics.json files.
  Q2 (attribution): one row per top SAE feature per (dataset, model, hook),
                   pulled from feature_scores.parquet.

Usage:
  python aggregate_metrics.py --sweep-root outputs/classifiers --out tutorials/classifiers/results
"""
import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    args = _parse_args()
    sweep_root = Path(args.sweep_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    probe_table = _collect_probes(sweep_root)
    if not probe_table.empty:
        probe_table.to_csv(out_dir / "probes.csv", index=False)
        (out_dir / "probes.md").write_text(_to_markdown(probe_table))
        print(f"probe rows: {len(probe_table)} -> {out_dir/'probes.md'}")

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
    cell_name = cell_dir.name              # e.g. rfd3_block6_sae_encode
    parts = cell_name.split("_")
    model, hook, extractor = parts[0], parts[1], "_".join(parts[2:])
    return {"dataset": dataset, "cell_name": cell_name,
            "model": model, "hook": hook, "extractor": extractor}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _flatten_probe_row(cell: dict) -> dict:
    row = {k: cell[k] for k in ("dataset", "model", "hook", "extractor")}
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
    return str(v)


if __name__ == "__main__":
    main()
