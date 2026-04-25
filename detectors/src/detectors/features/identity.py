import json
from dataclasses import dataclass
from pathlib import Path

import torch


@dataclass
class IdentityExtractor:
    feature_dim: int

    def transform(self, activations: torch.Tensor) -> torch.Tensor:
        return activations

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "extractor.json").write_text(
            json.dumps({"kind": "identity", "feature_dim": self.feature_dim})
        )

    @classmethod
    def load(cls, directory: Path) -> "IdentityExtractor":
        config = json.loads((directory / "extractor.json").read_text())
        return cls(feature_dim=int(config["feature_dim"]))
