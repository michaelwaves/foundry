"""Measure hazard-direction projection in activations across two steering sweeps:
  1. SAE feature 639 ablation (alpha = 0, 1, 2, 4, 8)
  2. Raw diff-of-means negative steering (coeff = 0, 1, 2, 4, 8)

Produces:
  outputs/steering/sweep/figures/activation_projection.pdf  — two-panel figure

Usage:
    python plot_activation_projection.py
"""
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import torch


_SWEEP_DIR = Path("outputs/steering/sweep")
_VECTOR_DIR = Path("outputs/steering/vectors/haz_minus_ben")
_HOOKS = ["block6", "block8", "block12"]
_HOOK_COLORS = {"block6": "#4e79a7", "block8": "#f28e2b", "block12": "#e15759"}

_ABLATION_RUNS = {0: "alpha0", 1: "alpha1", 2: "alpha2", 4: "alpha4", 8: "alpha8"}
_RAWDIFF_RUNS = {0: "alpha0", 1: "rawdiff_c1", 2: "rawdiff_c2", 4: "rawdiff_c4", 8: "rawdiff_c8"}


def main() -> None:
    vectors = _load_vectors()
    ablation = _compute_projections(vectors, _ABLATION_RUNS)
    rawdiff = _compute_projections(vectors, _RAWDIFF_RUNS)
    _plot(ablation, rawdiff)


def _load_vectors() -> dict[str, torch.Tensor]:
    return {
        hook: torch.load(_VECTOR_DIR / f"{hook}.pt", weights_only=True).float()
        for hook in _HOOKS
        if (_VECTOR_DIR / f"{hook}.pt").exists()
    }


def _compute_projections(
    vectors: dict[str, torch.Tensor],
    runs: dict[int, str],
) -> dict[str, dict[int, tuple[float, float]]]:
    results: dict[str, dict[int, tuple[float, float]]] = {h: {} for h in vectors}

    for coeff, run_name in runs.items():
        h5_path = _SWEEP_DIR / run_name / "activations" / "activations.h5"
        if not h5_path.exists():
            print(f"  missing {h5_path}, skipping")
            continue
        with h5py.File(h5_path, "r") as f:
            for hook, vec in vectors.items():
                if hook not in f:
                    continue
                projections = []
                for design_id in f[hook]:
                    for step_key in f[hook][design_id]:
                        arr = np.asarray(f[hook][design_id][step_key])
                        flat = arr.reshape(-1, arr.shape[-1])
                        proj = (torch.from_numpy(flat).float() @ vec).numpy()
                        projections.extend(proj.tolist())
                if projections:
                    results[hook][coeff] = (float(np.mean(projections)),
                                            float(np.std(projections)))

    return results


def _plot(
    ablation: dict[str, dict[int, tuple[float, float]]],
    rawdiff: dict[str, dict[int, tuple[float, float]]],
) -> None:
    out_dir = _SWEEP_DIR / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

    for hook, color in _HOOK_COLORS.items():
        for ax, data, title in [
            (ax1, ablation, "SAE feature 639 ablation"),
            (ax2, rawdiff, "Raw diff-of-means subtraction"),
        ]:
            if hook not in data or not data[hook]:
                continue
            xs = sorted(data[hook])
            means = [data[hook][x][0] for x in xs]
            stds = [data[hook][x][1] for x in xs]
            ax.errorbar(xs, means, yerr=[s / 20 for s in stds],
                        fmt="o-", color=color, label=hook,
                        capsize=3, linewidth=2, markersize=5)

    for ax, title in [(ax1, "SAE feature 639 ablation"),
                      (ax2, "Raw diff-of-means subtraction")]:
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Steering strength")
        ax.set_title(title)
        ax.set_xticks([0, 1, 2, 4, 8])

    ax1.set_ylabel("Mean projection onto hazard direction")
    ax1.legend(fontsize=9)
    fig.suptitle("Hazard direction in activations vs. steering strength", fontsize=12)
    fig.tight_layout()

    out_path = out_dir / "activation_projection.pdf"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
