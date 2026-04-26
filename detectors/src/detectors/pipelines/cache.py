from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import h5py
import numpy as np
import torch

from detectors.features import PoolingStrategy, pool_design
from detectors.features.identity import IdentityExtractor
from detectors.features.sae_encode import SAEEncodeExtractor


@dataclass
class FeatureCache:
    features: np.ndarray            # (N_rows, F)
    design_ids: np.ndarray          # (N_rows,) str
    sample_indices: np.ndarray      # (N_rows,) int


def build_feature_cache(config: dict, cache_path: Path) -> FeatureCache:
    extractor = build_extractor(config["extractor"])
    pooling = PoolingStrategy(config["pooling"])

    feature_chunks: list[np.ndarray] = []
    design_id_chunks: list[list[str]] = []
    sample_index_chunks: list[np.ndarray] = []

    for design_id, activations in _iter_design_activations(config["activations_path"], config["hook_name"]):
        encoded = extractor.transform(torch.from_numpy(activations).float())
        pooled = pool_design(encoded, pooling)
        features = pooled.numpy()
        n_samples = features.shape[0]
        feature_chunks.append(features)
        design_id_chunks.append([design_id] * n_samples)
        sample_index_chunks.append(np.arange(n_samples, dtype=np.int64))

    cache = FeatureCache(
        features=np.concatenate(feature_chunks, axis=0).astype(np.float32),
        design_ids=np.array(sum(design_id_chunks, []), dtype=object),
        sample_indices=np.concatenate(sample_index_chunks),
    )
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache_path, features=cache.features,
             design_ids=cache.design_ids, sample_indices=cache.sample_indices)
    return cache


def load_feature_cache(cache_path: Path) -> FeatureCache:
    data = np.load(cache_path, allow_pickle=True)
    return FeatureCache(
        features=data["features"],
        design_ids=data["design_ids"],
        sample_indices=data["sample_indices"],
    )


def build_extractor(spec: dict):
    if spec["kind"] == "identity":
        return IdentityExtractor(feature_dim=int(spec["feature_dim"]))
    if spec["kind"] == "sae_encode":
        return SAEEncodeExtractor.from_checkpoint(spec["checkpoint_path"], spec.get("device", "cpu"))
    raise ValueError(f"unknown extractor kind: {spec['kind']}")


def _iter_design_activations(activations_path: str, hook_name: str) -> Iterator[tuple[str, np.ndarray]]:
    with h5py.File(activations_path, "r") as f:
        if hook_name not in f:
            raise KeyError(f"hook '{hook_name}' not in {list(f.keys())}")
        hook_group = f[hook_name]
        for design_id in hook_group.keys():
            step_ids = sorted(hook_group[design_id].keys(), key=int)
            arrays = [hook_group[design_id][step_id][...] for step_id in step_ids]
            yield design_id, np.stack(arrays, axis=1)
