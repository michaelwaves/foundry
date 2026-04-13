from typing import Optional


class SAETrainer:
    """Base class for SAE training algorithms."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self.logging_parameters: list[str] = []

    def update(self, step: int, activations) -> float:
        raise NotImplementedError

    def get_logging_parameters(self) -> dict:
        return {p: getattr(self, p) for p in self.logging_parameters if hasattr(self, p)}

    @property
    def config(self) -> dict:
        raise NotImplementedError
