import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from detectors.scorers.auroc import auroc_vectorized


@dataclass
class TopFeatureThresholdDetector:
    """Pick the highest-AUROC feature, threshold it. Sanity baseline."""

    feature_index: int = -1
    threshold: float = 0.0
    polarity: int = 1  # +1 if higher = positive class, -1 otherwise

    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        scores = auroc_vectorized(features, labels)
        distances = np.abs(scores - 0.5)
        self.feature_index = int(np.argmax(distances))
        self.polarity = 1 if scores[self.feature_index] >= 0.5 else -1
        column = self.polarity * features[:, self.feature_index]
        positives = column[labels.astype(bool)]
        negatives = column[~labels.astype(bool)]
        self.threshold = float((positives.mean() + negatives.mean()) / 2.0)

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        column = self.polarity * features[:, self.feature_index]
        positive = 1.0 / (1.0 + np.exp(-(column - self.threshold)))
        return np.stack([1.0 - positive, positive], axis=1)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "detector.json").write_text(json.dumps({
            "kind": "top_feature", "feature_index": self.feature_index,
            "threshold": self.threshold, "polarity": self.polarity,
        }))

    @classmethod
    def load(cls, directory: Path) -> "TopFeatureThresholdDetector":
        config = json.loads((directory / "detector.json").read_text())
        return cls(feature_index=int(config["feature_index"]),
                   threshold=float(config["threshold"]),
                   polarity=int(config["polarity"]))
