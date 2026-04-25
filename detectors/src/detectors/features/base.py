from pathlib import Path
from typing import Protocol, runtime_checkable

import torch


@runtime_checkable
class FeatureExtractor(Protocol):
    feature_dim: int

    def transform(self, activations: torch.Tensor) -> torch.Tensor: ...
    def save(self, directory: Path) -> None: ...
    @classmethod
    def load(cls, directory: Path) -> "FeatureExtractor": ...
