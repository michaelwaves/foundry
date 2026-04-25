from enum import Enum

import torch


class PoolingStrategy(str, Enum):
    MAX = "max"
    MEAN = "mean"
    LAST_STEP = "last_step"
    PER_TOKEN = "per_token"


def pool_design(activations: torch.Tensor, strategy: PoolingStrategy) -> torch.Tensor:
    """Reduce (n_samples, n_steps, n_tokens, dim) → design-level features.

    PER_TOKEN keeps the token axis for per-residue scoring; others collapse to (n_samples, dim).
    """
    if activations.ndim != 4:
        raise ValueError(f"expected 4D (samples, steps, tokens, dim), got shape {tuple(activations.shape)}")

    if strategy is PoolingStrategy.MAX:
        return activations.amax(dim=(1, 2))
    if strategy is PoolingStrategy.MEAN:
        return activations.mean(dim=(1, 2))
    if strategy is PoolingStrategy.LAST_STEP:
        return activations[:, -1, :, :].mean(dim=1)
    if strategy is PoolingStrategy.PER_TOKEN:
        return activations[:, -1, :, :]
    raise ValueError(f"unknown strategy: {strategy}")
