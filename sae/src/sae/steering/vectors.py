from functools import lru_cache
from pathlib import Path

import torch

from sae.models.matryoshka_batch_topk import MatryoshkaBatchTopKSAE
from sae.steering.config import SteeringSpec


def direction_from_spec(spec: SteeringSpec) -> torch.Tensor:
    """Resolve a SteeringSpec to a (activation_dim,) direction vector.

    sae_feature → coeff * decoder_row(feature_id), unit-normalized then scaled by alpha.
    raw_diff    → coeff * unit_normalize(vector_from_disk).
    """
    if spec.mode == "sae_feature":
        decoder_row = _sae_decoder_row(spec.sae_path, spec.feature_id)
        return spec.alpha * _unit_normalize(decoder_row)
    if spec.mode == "raw_diff":
        raw = torch.load(spec.vector_path, map_location="cpu", weights_only=True)
        return spec.coeff * _unit_normalize(raw)
    raise ValueError(f"unknown steering mode: {spec.mode}")


@lru_cache(maxsize=8)
def _sae_decoder_row(checkpoint_path: str, feature_id: int) -> torch.Tensor:
    sae = _load_sae(checkpoint_path)
    return sae.W_dec[feature_id].detach().clone()


@lru_cache(maxsize=4)
def _load_sae(checkpoint_path: str) -> MatryoshkaBatchTopKSAE:
    checkpoint = torch.load(str(Path(checkpoint_path)), map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    sae = MatryoshkaBatchTopKSAE(
        config["activation_dim"], config["dict_size"],
        k=config["k"], group_sizes=config["group_sizes"],
    )
    sae.load_state_dict(checkpoint["ae"])
    return sae.eval()


def _unit_normalize(vector: torch.Tensor) -> torch.Tensor:
    norm = vector.norm()
    return vector / norm.clamp_min(1e-12)
