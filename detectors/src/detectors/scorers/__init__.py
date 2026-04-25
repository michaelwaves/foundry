from detectors.scorers.auroc import auroc_p_value, auroc_vectorized
from detectors.scorers.base import Scorer

SCORERS: dict[str, Scorer] = {
    "auroc": Scorer(auroc_vectorized, auroc_p_value, 0.5, "auroc", "auroc_p"),
}

__all__ = ["SCORERS", "Scorer"]
