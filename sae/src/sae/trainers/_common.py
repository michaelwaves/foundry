from typing import Callable, Optional

import torch


class ConstrainedAdam(torch.optim.Adam):
    """Adam that keeps decoder column norms at unit length."""

    def __init__(self, params, constrained_params, lr: float, betas=(0.9, 0.999)):
        super().__init__(params, lr=lr, betas=betas)
        self.constrained_params = list(constrained_params)

    def step(self, closure=None):
        with torch.no_grad():
            for param in self.constrained_params:
                normed = param / param.norm(dim=0, keepdim=True)
                param.grad -= (param.grad * normed).sum(dim=0, keepdim=True) * normed
        super().step(closure=closure)
        with torch.no_grad():
            for param in self.constrained_params:
                param /= param.norm(dim=0, keepdim=True)


def get_lr_schedule(
    total_steps: int,
    warmup_steps: int,
    decay_start: Optional[int] = None,
) -> Callable[[int], float]:
    assert 0 <= warmup_steps < total_steps
    if decay_start is not None:
        assert warmup_steps < decay_start < total_steps

    def schedule(step: int) -> float:
        if step < warmup_steps:
            return step / warmup_steps
        if decay_start is not None and step >= decay_start:
            return (total_steps - step) / (total_steps - decay_start)
        return 1.0

    return schedule


def geometric_median(points: torch.Tensor, max_iter: int = 100, tol: float = 1e-5) -> torch.Tensor:
    guess = points.mean(dim=0)
    for _ in range(max_iter):
        prev = guess
        weights = 1 / torch.norm(points - guess, dim=1).clamp(min=1e-8)
        weights /= weights.sum()
        guess = (weights.unsqueeze(1) * points).sum(dim=0)
        if torch.norm(guess - prev) < tol:
            break
    return guess
