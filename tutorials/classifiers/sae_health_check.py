#!/usr/bin/env python3
"""Print SAE reconstruction + sparsity + alive-feature stats for every trained SAE.

Skips the interpretability stack (PyMOL rendering, top-firing-tokens) — just
the headline numbers from sae.evaluation.compute_metrics. Run this when a
sweep produces low SAE feature utilization to decide whether the SAE itself is
healthy or needs more training.

Usage:
  python sae_health_check.py
"""
import json
from pathlib import Path

import torch

from sae.dataset import ActivationLoaderConfig, build_activation_loader
from sae.evaluation import compute_metrics
from sae.models.matryoshka_batch_topk import MatryoshkaBatchTopKSAE


ROOT = Path("/mnt/nw/home/m.yu/repos/foundry")
DEVICE = "cpu"
BATCH_SIZE = 4096


def main() -> None:
    cells = [
        (
            "rfd3_safeprotein", hook,
            ROOT / f"outputs/sae/2026-04-26_15-38-55/train/{hook}/final.pt",
            ROOT / "tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5",
        )
        for hook in ("block6", "block8", "block12")
    ] + [
        (
            "rf3_toxinpred3", hook,
            ROOT / f"outputs/sae/2026-04-26_15-23-45/train/{hook}/final.pt",
            ROOT / "tutorials/sae_data_rf3/train_activations/activations/activations.h5",
        )
        for hook in ("block12", "block16")
    ]

    print(f"{'dataset':<20s} {'hook':<8s} {'k':>4s} {'l0':>6s} {'frac_alive':>11s} {'fve':>7s} {'cossim':>7s} {'n_tok':>8s}")
    for dataset, hook, ckpt, h5 in cells:
        sae = _load_sae(ckpt)
        loader, _ = build_activation_loader(ActivationLoaderConfig(
            activations_path=str(h5), hook_name=hook,
            batch_size=BATCH_SIZE, shuffle=False,
        ))
        tokens = loader.dataset.tensors[0]
        metrics = compute_metrics(sae, tokens, batch_size=BATCH_SIZE)
        print(f"{dataset:<20s} {hook:<8s} {sae.k:>4d} {metrics.l0:>6.1f} "
              f"{metrics.frac_alive:>11.3f} {metrics.frac_variance_explained:>7.3f} "
              f"{metrics.cossim:>7.3f} {metrics.n_tokens:>8d}")


def _load_sae(checkpoint_path: Path) -> torch.nn.Module:
    checkpoint = torch.load(str(checkpoint_path), map_location=DEVICE, weights_only=False)
    config = checkpoint["config"]
    sae = MatryoshkaBatchTopKSAE(
        config["activation_dim"], config["dict_size"],
        k=config["k"], group_sizes=config["group_sizes"],
    )
    sae.load_state_dict(checkpoint["ae"])
    return sae.to(DEVICE).eval()


if __name__ == "__main__":
    main()
