from dataclasses import dataclass, field
from typing import Iterable

import torch

from sae.evaluation.activations import DesignActivations


@dataclass
class FeatureStats:
    """Per-feature accumulators across all designs/samples/steps/tokens."""

    dict_size: int
    max_activation: torch.Tensor  # (F,)
    fire_count: torch.Tensor       # (F,)
    token_count: int = 0
    per_design: dict = field(default_factory=dict)  # {design_id: (n_tokens, F) mean activation}


@torch.no_grad()
def build_feature_stats(
    sae: torch.nn.Module,
    designs: Iterable[DesignActivations],
    batch_size: int = 4096,
) -> FeatureStats:
    sae.eval()
    device = next(sae.parameters()).device
    stats = FeatureStats(
        dict_size=sae.dict_size,
        max_activation=torch.zeros(sae.dict_size, device=device),
        fire_count=torch.zeros(sae.dict_size, device=device),
    )

    for design in designs:
        per_token_sum = torch.zeros(design.n_tokens, sae.dict_size, device=device)
        flat = design.flat_tokens().to(device=device, dtype=torch.float32)
        features = _encode_in_chunks(sae, flat, batch_size)

        stats.max_activation = torch.maximum(stats.max_activation, features.max(dim=0).values)
        stats.fire_count += (features != 0).float().sum(dim=0)
        stats.token_count += features.shape[0]

        reshaped = features.reshape(design.n_samples, design.n_steps, design.n_tokens, -1)
        per_token_sum = reshaped.mean(dim=(0, 1))  # (n_tokens, F)
        stats.per_design[design.design_id] = per_token_sum.cpu()

    return stats


def pick_interesting_features(
    stats: FeatureStats,
    num_features: int = 12,
    min_fires: int = 10,
) -> list[int]:
    """Features that fire strongly but sparsely, and are spatially concentrated."""
    fire_rate = stats.fire_count / max(stats.token_count, 1)
    sparsity_score = 1.0 / (fire_rate.clamp(min=1e-6))
    strength_score = stats.max_activation

    concentration = _mean_concentration_across_designs(stats)
    alive = (stats.fire_count >= min_fires).float()

    score = (strength_score * sparsity_score.log1p() * concentration * alive).cpu()
    return torch.topk(score, k=min(num_features, int(alive.sum().item()))).indices.tolist()


def top_firing_tokens(
    stats: FeatureStats, feature_id: int, top_k: int = 5
) -> dict[str, list[tuple[int, float]]]:
    """For each design, return top-k (token_index, mean_activation) for the feature."""
    output: dict[str, list[tuple[int, float]]] = {}
    for design_id, per_token in stats.per_design.items():
        column = per_token[:, feature_id]
        k = min(top_k, column.shape[0])
        values, indices = column.topk(k)
        output[design_id] = list(zip(indices.tolist(), values.tolist()))
    return output


def _encode_in_chunks(sae, flat: torch.Tensor, batch_size: int) -> torch.Tensor:
    chunks = [sae.encode(flat[i : i + batch_size]) for i in range(0, flat.shape[0], batch_size)]
    return torch.cat(chunks, dim=0)


def _mean_concentration_across_designs(stats: FeatureStats) -> torch.Tensor:
    """For each feature, 1 - normalized entropy of its per-token activation distribution."""
    per_feature = []
    for per_token in stats.per_design.values():
        weights = per_token.clamp(min=0).cpu()
        totals = weights.sum(dim=0, keepdim=True).clamp(min=1e-12)
        probabilities = weights / totals
        entropy = -(probabilities * probabilities.clamp(min=1e-12).log()).sum(dim=0)
        max_entropy = torch.log(torch.tensor(per_token.shape[0], dtype=torch.float32))
        per_feature.append(1.0 - entropy / max_entropy)
    return torch.stack(per_feature, dim=0).mean(dim=0).to(stats.max_activation.device)
