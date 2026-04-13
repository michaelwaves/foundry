from dataclasses import dataclass

import h5py
import torch
from torch.utils.data import DataLoader, TensorDataset


@dataclass
class ActivationLoaderConfig:
    activations_path: str
    hook_name: str
    batch_size: int
    shuffle: bool = True
    dtype: torch.dtype = torch.float32


def build_activation_loader(cfg: ActivationLoaderConfig) -> tuple[DataLoader, int]:
    """Load all tokens for one hook into memory, return (DataLoader, activation_dim)."""
    tokens = _load_tokens(cfg.activations_path, cfg.hook_name).to(cfg.dtype)
    activation_dim = tokens.shape[-1]
    loader = DataLoader(
        TensorDataset(tokens),
        batch_size=cfg.batch_size,
        shuffle=cfg.shuffle,
        drop_last=True,
    )
    return loader, activation_dim


def _load_tokens(activations_path: str, hook_name: str) -> torch.Tensor:
    chunks: list[torch.Tensor] = []
    with h5py.File(activations_path, "r") as f:
        if hook_name not in f:
            raise KeyError(f"hook '{hook_name}' not in {list(f.keys())}")
        group = f[hook_name]
        for example_id in group.keys():
            example_group = group[example_id]
            for step_id in example_group.keys():
                array = example_group[step_id][...]
                chunks.append(torch.from_numpy(array).reshape(-1, array.shape[-1]))
    return torch.cat(chunks, dim=0)
