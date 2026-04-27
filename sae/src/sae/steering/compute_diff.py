"""Offline computation of mean-difference steering vectors per hook.

Reads an activations h5 + labels CSV, takes the per-token mean across all
tokens (across all designs/steps/samples) for each class, computes
mean(positives) − mean(negatives), optionally unit-normalizes, writes one
`<hook>.pt` per hook to out_dir.

Inputs JSON / Hydra config keys:
  activations_h5: path to a saffron-collect h5
  labels_csv:     CSV with columns design_id,label (matches detect labels output)
  positive_label: which label value counts as positive (default 1)
  negative_label: which label value counts as negative (default 0)
  hooks:          list of hook names to compute vectors for
  normalize:      "unit" (default) | "none"
"""
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch
from omegaconf import DictConfig


def run_compute_diff(cfg: DictConfig) -> None:
    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = pd.read_csv(cfg.labels_csv).set_index("design_id")["label"]
    positive_ids = set(labels[labels == int(cfg.get("positive_label", 1))].index)
    negative_ids = set(labels[labels == int(cfg.get("negative_label", 0))].index)
    summaries: list[dict] = []

    for hook in list(cfg.hooks):
        pos_mean, n_pos = _per_token_mean(cfg.activations_h5, hook, positive_ids)
        neg_mean, n_neg = _per_token_mean(cfg.activations_h5, hook, negative_ids)
        diff = pos_mean - neg_mean
        raw_norm = float(diff.norm())
        if cfg.get("normalize", "unit") == "unit":
            diff = diff / diff.norm().clamp_min(1e-12)

        torch.save(diff, out_dir / f"{hook}.pt")
        summaries.append({
            "hook": hook, "dim": int(diff.shape[0]),
            "n_positive_tokens": int(n_pos), "n_negative_tokens": int(n_neg),
            "norm_before_normalize": raw_norm,
        })
        print(f"{hook}: dim={diff.shape[0]}, n_pos={n_pos}, n_neg={n_neg}, "
              f"raw_norm={raw_norm:.3f}")

    (out_dir / "meta.json").write_text(json.dumps({
        "activations_h5": cfg.activations_h5,
        "labels_csv": cfg.labels_csv,
        "positive_label": int(cfg.get("positive_label", 1)),
        "negative_label": int(cfg.get("negative_label", 0)),
        "normalize": cfg.get("normalize", "unit"),
        "hooks": summaries,
    }, indent=2))


def _per_token_mean(activations_path: str, hook: str, design_ids: set[str]) -> tuple[torch.Tensor, int]:
    sum_vec: torch.Tensor | None = None
    token_count = 0
    with h5py.File(activations_path, "r") as f:
        if hook not in f:
            raise KeyError(f"hook {hook!r} not in {list(f.keys())}")
        for design_id in f[hook].keys():
            if design_id not in design_ids:
                continue
            for step_id in f[hook][design_id].keys():
                arr = np.asarray(f[hook][design_id][step_id][...])  # (..., dim)
                flat = arr.reshape(-1, arr.shape[-1])
                t = torch.from_numpy(flat).float().sum(dim=0)
                sum_vec = t if sum_vec is None else sum_vec + t
                token_count += flat.shape[0]
    if sum_vec is None or token_count == 0:
        raise RuntimeError(
            f"no tokens found for hook {hook!r} in {activations_path} "
            f"matching {len(design_ids)} design_ids"
        )
    return sum_vec / token_count, token_count
