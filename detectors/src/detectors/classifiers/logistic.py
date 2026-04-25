import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch


@dataclass
class LogisticDetector:
    """Binary logistic regression in pure torch with L2 regularization."""

    epochs: int = 200
    lr: float = 0.05
    weight_decay: float = 1e-4
    weights: torch.Tensor = field(default_factory=lambda: torch.zeros(0))
    bias: torch.Tensor = field(default_factory=lambda: torch.zeros(1))

    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        x, y = _to_tensors(features, labels)
        self.weights = torch.zeros(x.shape[1], requires_grad=True)
        self.bias = torch.zeros(1, requires_grad=True)
        optimizer = torch.optim.Adam(
            [self.weights, self.bias], lr=self.lr, weight_decay=self.weight_decay
        )
        loss_fn = torch.nn.BCEWithLogitsLoss()
        for _ in range(self.epochs):
            optimizer.zero_grad()
            logits = x @ self.weights + self.bias
            loss_fn(logits, y).backward()
            optimizer.step()
        self.weights = self.weights.detach()
        self.bias = self.bias.detach()

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        x = torch.from_numpy(features.astype(np.float32))
        with torch.no_grad():
            positive = torch.sigmoid(x @ self.weights + self.bias).numpy()
        return np.stack([1.0 - positive, positive], axis=1)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        torch.save({"weights": self.weights, "bias": self.bias}, directory / "detector.pt")
        (directory / "detector.json").write_text(json.dumps({
            "kind": "logistic", "epochs": self.epochs, "lr": self.lr, "weight_decay": self.weight_decay,
        }))

    @classmethod
    def load(cls, directory: Path) -> "LogisticDetector":
        config = json.loads((directory / "detector.json").read_text())
        state = torch.load(directory / "detector.pt", map_location="cpu", weights_only=True)
        instance = cls(epochs=int(config["epochs"]), lr=float(config["lr"]),
                       weight_decay=float(config["weight_decay"]))
        instance.weights = state["weights"]
        instance.bias = state["bias"]
        return instance


def _to_tensors(features: np.ndarray, labels: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
    x = torch.from_numpy(features.astype(np.float32))
    y = torch.from_numpy(labels.astype(np.float32))
    return x, y
