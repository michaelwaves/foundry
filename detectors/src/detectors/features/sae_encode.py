import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import torch

from sae.models.matryoshka_batch_topk import MatryoshkaBatchTopKSAE


@dataclass
class SAEEncodeExtractor:
    sae: torch.nn.Module
    feature_dim: int
    checkpoint_path: str
    device: str

    @classmethod
    def from_checkpoint(cls, checkpoint_path: str, device: str = "cpu") -> "SAEEncodeExtractor":
        sae = _load_sae(checkpoint_path, device)
        return cls(sae=sae, feature_dim=int(sae.dict_size), checkpoint_path=checkpoint_path, device=device)

    @torch.no_grad()
    def transform(self, activations: torch.Tensor) -> torch.Tensor:
        moved = activations.to(self.device).to(next(self.sae.parameters()).dtype)
        encoded = self.sae.encode(moved)
        return encoded.cpu().float()

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        local_checkpoint = directory / "sae.pt"
        if Path(self.checkpoint_path).resolve() != local_checkpoint.resolve():
            shutil.copy(self.checkpoint_path, local_checkpoint)
        (directory / "extractor.json").write_text(
            json.dumps({"kind": "sae_encode", "feature_dim": self.feature_dim, "device": self.device})
        )

    @classmethod
    def load(cls, directory: Path) -> "SAEEncodeExtractor":
        config = json.loads((directory / "extractor.json").read_text())
        return cls.from_checkpoint(str(directory / "sae.pt"), device=config.get("device", "cpu"))


def _load_sae(checkpoint_path: str, device: str) -> torch.nn.Module:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state_dict = checkpoint.get("ae", checkpoint)
    config = checkpoint.get("config")
    if config is not None:
        sae = MatryoshkaBatchTopKSAE(
            config["activation_dim"], config["dict_size"], k=config["k"], group_sizes=config["group_sizes"]
        )
        sae.load_state_dict(state_dict)
    else:
        sae = MatryoshkaBatchTopKSAE.from_pretrained(checkpoint_path)
    return sae.to(device).eval()
