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
    per_design: dict = field(default_factory=dict)  # {design_id: (n_samples, n_tokens, F) mean over steps}


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
        flat = design.flat_tokens().to(device=device, dtype=torch.float32)
        features = _encode_in_chunks(sae, flat, batch_size)

        stats.max_activation = torch.maximum(stats.max_activation, features.max(dim=0).values)
        stats.fire_count += (features != 0).float().sum(dim=0)
        stats.token_count += features.shape[0]

        reshaped = features.reshape(design.n_samples, design.n_steps, design.n_tokens, -1)
        per_sample_token = reshaped.mean(dim=1)  # (n_samples, n_tokens, F)
        stats.per_design[design.design_id] = per_sample_token.cpu()

    return stats


def pick_interesting_features(
    stats: FeatureStats,
    num_features: int = 12,
    min_fires: int = 10,
) -> list[int]:
    """Features that fire strongly but sparsely across designs."""
    fire_rate = stats.fire_count / max(stats.token_count, 1)
    sparsity_score = 1.0 / (fire_rate.clamp(min=1e-6))
    strength_score = stats.max_activation
    alive = (stats.fire_count >= min_fires).float()

    score = (strength_score * sparsity_score.log1p() * alive).cpu()
    return torch.topk(score, k=min(num_features, int(alive.sum().item()))).indices.tolist()


def top_firing_tokens(
    stats: FeatureStats,
    feature_id: int,
    top_k: int = 5,
    min_activation_fraction: float = 0.05,
) -> dict[str, list[tuple[int, int, float]]]:
    """For each design, return (sample_idx, token_index, mean_activation) tuples where
    the feature actually fires, up to top_k across all (sample, token) positions.
    Empty list when the feature is silent on that design."""
    feature_max = float(stats.max_activation[feature_id].item())
    threshold = max(min_activation_fraction * feature_max, 1e-6)
    output: dict[str, list[tuple[int, int, float]]] = {}
    for design_id, per_sample_token in stats.per_design.items():
        slab = per_sample_token[:, :, feature_id]  # (n_samples, n_tokens)
        n_samples, n_tokens = slab.shape
        flat = slab.reshape(-1)
        k = min(top_k, flat.shape[0])
        values, indices = flat.topk(k)
        hits = []
        for idx, v in zip(indices.tolist(), values.tolist()):
            if v <= threshold:
                continue
            sample_idx = idx // n_tokens
            token_idx = idx % n_tokens
            hits.append((int(sample_idx), int(token_idx), float(v)))
        output[design_id] = hits
    return output


def _encode_in_chunks(sae, flat: torch.Tensor, batch_size: int) -> torch.Tensor:
    chunks = [sae.encode(flat[i : i + batch_size]) for i in range(0, flat.shape[0], batch_size)]
    return torch.cat(chunks, dim=0)
