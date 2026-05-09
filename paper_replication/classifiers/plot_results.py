#!/usr/bin/env python3
"""Render PNG bar charts comparing random vs homology-clustered splits
(both under stop_overfit hyperparameters) plus the top SAE feature attribution.

Outputs land in tutorials/classifiers/results_cluster_stop_overfit/figures/.

Usage:
  python plot_results.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).parent
RESULTS = HERE / "results_cluster_stop_overfit" / "figures"
RANDOM_CSV = HERE / "results_stop_overfitting" / "probes.csv"
CLUSTER_CSV = HERE / "results_cluster_stop_overfit" / "probes.csv"
TOP_FEATURES_CSV = HERE / "results" / "top_features.csv"

# Published absolute AUROCs on bacterial-VF benchmarks. Our score is RFD3 block12
# sae_encode under the random split (results_stop_overfitting/probes.csv).
SOTA_AUROC = (
    ("VF-Pred (Singh+, 2024)", 0.84, "#999999"),
    ("VirulentPred 1.0 (Garg & Gupta, 2008)", 0.86, "#999999"),
    ("RFD3 block12 SAE (ours)", 0.877, "#dd8452"),
    ("DTVF (Sun+, 2024)", 0.92, "#999999"),
)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": ":",
    })

    random_df, cluster_df = _load_probes(RANDOM_CSV, CLUSTER_CSV)

    _plot_random_vs_cluster(random_df, cluster_df, RESULTS / "01_random_vs_cluster.png")
    _plot_overfitting_gap(random_df, cluster_df, RESULTS / "02_train_vs_eval_gap.png")
    _plot_sae_vs_raw_delta(random_df, cluster_df, RESULTS / "03_sae_vs_raw_delta.png")
    _plot_top_features(TOP_FEATURES_CSV, RESULTS / "04_top_hazard_features.png")
    _plot_sota_comparison(RESULTS / "05_sota_comparison.png")
    print(f"wrote 5 figures to {RESULTS}")


def _load_probes(random_path: Path, cluster_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    def _prep(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path)
        df = df[df.dataset.str.endswith("_safeprotein")].reset_index(drop=True)
        df["cell"] = df["model"].str.upper() + " " + df["hook"]
        return df
    return _prep(random_path), _prep(cluster_path)


def _plot_random_vs_cluster(random_df: pd.DataFrame, cluster_df: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
    bar_handles = []
    for ax, extractor, title in zip(axes, ("identity", "sae_encode"), ("Raw activations", "SAE-encoded")):
        rd = random_df[random_df.extractor == extractor].sort_values(["model", "hook"])
        cd = cluster_df[cluster_df.extractor == extractor].sort_values(["model", "hook"])
        labels = rd["cell"].tolist()
        x = np.arange(len(labels))
        width = 0.38

        b1 = ax.bar(x - width/2, rd.eval_auroc_mean, width, yerr=rd.eval_auroc_std,
                    label="Random split", color="#4c72b0", capsize=3, edgecolor="white", linewidth=0.5)
        b2 = ax.bar(x + width/2, cd.eval_auroc_mean, width, yerr=cd.eval_auroc_std,
                    label="Homology-clustered split", color="#dd8452", capsize=3, edgecolor="white", linewidth=0.5)
        if not bar_handles:
            bar_handles = [b1, b2]
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_ylim(0.4, 1.0)
        ax.set_title(title)
        ax.set_ylabel("Eval AUROC (mean ± 1σ over 5 folds)")

    fig.suptitle("Probe AUROC: random vs homology-clustered splits", fontsize=12, y=1.02)
    fig.legend(bar_handles, ["Random split", "Homology-clustered split"],
               loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_overfitting_gap(random_df: pd.DataFrame, cluster_df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    rows = []
    for variant_label, df in (("Random", random_df), ("Cluster", cluster_df)):
        for _, r in df.iterrows():
            rows.append({
                "label": f"{r['model'].upper()} {r['hook']} {r['extractor']}",
                "variant": variant_label,
                "train": r["train_train_auroc_mean"],
                "eval": r["eval_auroc_mean"],
                "gap": r["train_train_auroc_mean"] - r["eval_auroc_mean"],
            })
    g = pd.DataFrame(rows)
    rfd3_g = g[g.label.str.startswith("RFD3")].sort_values(["label", "variant"])
    labels = rfd3_g[rfd3_g.variant == "Random"]["label"].tolist()
    x = np.arange(len(labels))
    width = 0.38

    ax.bar(x - width/2, rfd3_g[rfd3_g.variant == "Random"].gap, width,
           label="Random", color="#4c72b0", edgecolor="white", linewidth=0.5)
    ax.bar(x + width/2, rfd3_g[rfd3_g.variant == "Cluster"].gap, width,
           label="Cluster", color="#dd8452", edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Train AUROC − Eval AUROC  (overfitting gap)")
    ax.set_title("Random vs Homologous Clustering")
    ax.legend(frameon=False)
    ax.axhline(0, color="black", linewidth=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_sae_vs_raw_delta(random_df: pd.DataFrame, cluster_df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    rows = []
    for variant_label, df in (("Random", random_df), ("Cluster", cluster_df)):
        for cell, group in df.groupby("cell"):
            id_row = group[group.extractor == "identity"].iloc[0]
            sae_row = group[group.extractor == "sae_encode"].iloc[0]
            rows.append({
                "cell": cell, "variant": variant_label,
                "delta": sae_row.eval_auroc_mean - id_row.eval_auroc_mean,
            })
    delta_df = pd.DataFrame(rows)
    cells = sorted(delta_df.cell.unique())
    x = np.arange(len(cells))
    width = 0.38

    rand = delta_df[delta_df.variant == "Random"].set_index("cell").reindex(cells).delta
    clus = delta_df[delta_df.variant == "Cluster"].set_index("cell").reindex(cells).delta
    ax.bar(x - width/2, rand, width, color="#4c72b0", label="Random split", edgecolor="white", linewidth=0.5)
    ax.bar(x + width/2, clus, width, color="#dd8452", label="Cluster split", edgecolor="white", linewidth=0.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(cells, rotation=30, ha="right")
    ax.set_ylabel("Eval AUROC delta:  SAE − raw")
    ax.set_title("SAE vs Raw Activations AUROC")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_top_features(parquet_csv: Path, out_path: Path) -> None:
    df = pd.read_csv(parquet_csv)
    df = df[(df.extractor == "sae_encode") & df.dataset.str.endswith("_safeprotein") & (df.auroc > 0.5)]
    cells = [
        ("rfd3_safeprotein", "block6"),  ("rfd3_safeprotein", "block8"),  ("rfd3_safeprotein", "block12"),
        ("rf3_safeprotein",  "block12"), ("rf3_safeprotein",  "block16"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))   # sharey=False so each panel labels its own features
    for ax, (dataset, hook) in zip(axes.flat, cells):
        sub = df[(df.dataset == dataset) & (df.hook == hook)].sort_values("auroc", ascending=False).head(10)
        title = f"{dataset.split('_')[0].upper()} {hook}"
        if sub.empty:
            ax.set_title(f"{title} (no hazard features)")
            ax.set_xticks([]); ax.set_yticks([])
            continue
        y = np.arange(len(sub))[::-1]
        bars = ax.barh(y, sub.auroc, color="#c44e52", edgecolor="white", linewidth=0.5)
        for bar, q in zip(bars, sub.q_value):
            ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                    f"q={q:.1e}" if q < 1e-3 else f"q={q:.3f}",
                    va="center", fontsize=8, color="dimgray")
        ax.set_yticks(y)
        ax.set_yticklabels([f"#{int(f)}" for f in sub.feature_id])
        ax.axvline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_xlim(0.5, max(0.85, sub.auroc.max() * 1.12))
        ax.set_title(title)
        ax.set_xlabel("AUROC vs hazard")
    # Hide the empty 6th slot
    axes.flat[len(cells)].set_visible(False)
    fig.suptitle("Top hazard-firing SAE features per (model, hook) — BH-FDR corrected", fontsize=13, y=1.00)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_sota_comparison(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    labels, scores, colors = zip(*SOTA_AUROC)
    x = np.arange(len(labels))
    bars = ax.bar(x, scores, color=colors, edgecolor="white", linewidth=0.5, width=0.6)
    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{score:.2f}", ha="center", va="bottom", fontsize=10)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("Eval AUROC")
    ax.set_title("Virulence Factor Classification: Ours vs Published SOTA")
    fig.text(0.5, -0.02,
             "VirulentHunter (Chen+, 2025) reports relative AUC gains over MP4/DeepVF "
             "but no absolute AUROC, so it is omitted from this chart.",
             ha="center", fontsize=8, color="dimgray")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
