"""Plot DTVF virulence score and structural quality vs steering alpha.

Produces three figures saved to outputs/steering/sweep/figures/:
  1. virulence_vs_alpha.pdf   — DTVF score (mean ± std) vs alpha
  2. structure_vs_alpha.pdf   — max_ca_deviation and ss_fraction vs alpha
  3. tradeoff_scatter.pdf     — DTVF score vs max_ca_deviation, alpha as colour

Usage:
    python plot_results.py --sweep_dir outputs/steering/sweep \
                           --scores    outputs/steering/sweep/dtvf_scores.csv
"""
import glob
import json
from pathlib import Path

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


_ALPHAS = [0, 1, 2, 4, 8]
_ALPHA_LABELS = {0: "0 (null)", 1: "1", 2: "2", 4: "4", 8: "8"}
_COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]


@click.command()
@click.option("--sweep_dir", default="outputs/steering/sweep", type=click.Path())
@click.option("--scores", default="outputs/steering/sweep/dtvf_scores.csv", type=click.Path(exists=True))
def main(sweep_dir: str, scores: str) -> None:
    out_dir = Path(sweep_dir) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    dtvf_df = pd.read_csv(scores)
    struct_df = _load_structural_metrics(Path(sweep_dir))

    _plot_virulence(dtvf_df, out_dir)
    _plot_structure(struct_df, out_dir)
    _plot_tradeoff(dtvf_df, struct_df, out_dir)
    print(f"figures written to {out_dir}")


def _load_structural_metrics(sweep_dir: Path) -> pd.DataFrame:
    rows = []
    for alpha in _ALPHAS:
        for json_path in sorted((sweep_dir / f"alpha{alpha}").glob("*.json")):
            try:
                data = json.loads(json_path.read_text())
            except Exception:
                continue
            m = data.get("metrics", {})
            helix = m.get("helix_fraction", np.nan)
            sheet = m.get("sheet_fraction", np.nan)
            ss = (helix or 0) + (sheet or 0) if not (np.isnan(helix) or np.isnan(sheet)) else np.nan
            rows.append({
                "alpha": alpha,
                "design_id": json_path.stem,
                "max_ca_deviation": m.get("max_ca_deviation", np.nan),
                "ss_fraction": ss,
                "n_chainbreaks": m.get("n_chainbreaks", np.nan),
            })
    return pd.DataFrame(rows)


def _plot_virulence(df: pd.DataFrame, out_dir: Path) -> None:
    df["alpha_int"] = df["alpha"].str.replace("alpha", "").astype(int)
    grouped = df.groupby("alpha_int")["virulence_prob"]
    alphas = sorted(grouped.groups)
    means = [grouped.get_group(a).mean() for a in alphas]
    stds = [grouped.get_group(a).std() for a in alphas]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.errorbar(alphas, means, yerr=stds, fmt="o-", color="#e15759",
                capsize=4, linewidth=2, markersize=6)
    ax.axhline(means[0], linestyle="--", color="gray", linewidth=1, label="baseline (α=0)")
    ax.set_xlabel("Steering strength α")
    ax.set_ylabel("DTVF virulence probability")
    ax.set_title("Virulence score vs. ablation strength")
    ax.set_xticks(alphas)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "virulence_vs_alpha.pdf")
    plt.close(fig)
    print("virulence_vs_alpha.pdf saved")


def _plot_structure(df: pd.DataFrame, out_dir: Path) -> None:
    grouped_dev = df.groupby("alpha")["max_ca_deviation"]
    grouped_ss = df.groupby("alpha")["ss_fraction"]
    alphas = sorted(grouped_dev.groups)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))

    means_dev = [grouped_dev.get_group(a).mean() for a in alphas]
    stds_dev = [grouped_dev.get_group(a).std() for a in alphas]
    ax1.errorbar(alphas, means_dev, yerr=stds_dev, fmt="s-", color="#4e79a7",
                 capsize=4, linewidth=2, markersize=6)
    ax1.set_xlabel("Steering strength α")
    ax1.set_ylabel("Max CA deviation (Å)")
    ax1.set_title("Structural deviation vs. α")
    ax1.set_xticks(alphas)

    means_ss = [grouped_ss.get_group(a).mean() for a in alphas]
    stds_ss = [grouped_ss.get_group(a).std() for a in alphas]
    ax2.errorbar(alphas, means_ss, yerr=stds_ss, fmt="^-", color="#76b7b2",
                 capsize=4, linewidth=2, markersize=6)
    ax2.set_xlabel("Steering strength α")
    ax2.set_ylabel("Secondary structure fraction")
    ax2.set_title("Secondary structure vs. α")
    ax2.set_xticks(alphas)

    fig.tight_layout()
    fig.savefig(out_dir / "structure_vs_alpha.pdf")
    plt.close(fig)
    print("structure_vs_alpha.pdf saved")


def _plot_tradeoff(dtvf_df: pd.DataFrame, struct_df: pd.DataFrame, out_dir: Path) -> None:
    dtvf_df = dtvf_df.copy()
    dtvf_df["alpha_int"] = dtvf_df["alpha"].str.replace("alpha", "").astype(int)

    # match on design_id stem (strip alpha-prefixed design_id from dtvf)
    merged = struct_df.merge(
        dtvf_df[["design_id", "alpha_int", "virulence_prob"]],
        left_on=["design_id", "alpha"],
        right_on=["design_id", "alpha_int"],
        how="inner",
    )

    fig, ax = plt.subplots(figsize=(5, 4))
    for i, alpha in enumerate(_ALPHAS):
        sub = merged[merged["alpha"] == alpha]
        ax.scatter(sub["virulence_prob"], sub["max_ca_deviation"],
                   label=f"α={alpha}", color=_COLORS[i], alpha=0.7, s=30)

    ax.set_xlabel("DTVF virulence probability")
    ax.set_ylabel("Max CA deviation (Å)")
    ax.set_title("Safety–structure tradeoff")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "tradeoff_scatter.pdf")
    plt.close(fig)
    print("tradeoff_scatter.pdf saved")


if __name__ == "__main__":
    main()
