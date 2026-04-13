from collections import namedtuple
from typing import Optional

import torch

from sae.models.autoencoder import AutoEncoder
from sae.trainers._common import ConstrainedAdam, get_lr_schedule
from sae.trainers.base import SAETrainer


LossLog = namedtuple("LossLog", ["x", "x_hat", "f", "losses"])


class StandardTrainer(SAETrainer):
    """L1-penalized ReLU SAE (Towards Monosemanticity)."""

    def __init__(
        self,
        steps: int,
        activation_dim: int,
        dict_size: int,
        layer: int,
        lm_name: str,
        lr: float = 1e-3,
        l1_penalty: float = 1e-1,
        warmup_steps: int = 1000,
        sparsity_warmup_steps: Optional[int] = 2000,
        decay_start: Optional[int] = None,
        seed: Optional[int] = None,
        device: Optional[str] = None,
        wandb_name: str = "StandardTrainer",
        submodule_name: Optional[str] = None,
    ):
        super().__init__(seed)
        if seed is not None:
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

        self.steps = steps
        self.layer = layer
        self.lm_name = lm_name
        self.submodule_name = submodule_name
        self.wandb_name = wandb_name
        self.lr = lr
        self.l1_penalty = l1_penalty
        self.warmup_steps = warmup_steps
        self.sparsity_warmup_steps = sparsity_warmup_steps
        self.decay_start = decay_start
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.ae = AutoEncoder(activation_dim, dict_size).to(self.device)

        self.optimizer = ConstrainedAdam(
            self.ae.parameters(), self.ae.decoder.parameters(), lr=lr
        )
        self.scheduler = torch.optim.lr_scheduler.LambdaLR(
            self.optimizer, lr_lambda=get_lr_schedule(steps, warmup_steps, decay_start)
        )
        self.logging_parameters = []

    def _sparsity_scale(self, step: int) -> float:
        if not self.sparsity_warmup_steps:
            return 1.0
        return min(step / self.sparsity_warmup_steps, 1.0)

    def loss(self, x: torch.Tensor, step: int, logging: bool = False):
        x_hat, features = self.ae(x, output_features=True)
        recon_loss = (x - x_hat).pow(2).sum(dim=-1).mean()
        l1_loss = features.norm(p=1, dim=-1).mean()
        total = recon_loss + self.l1_penalty * self._sparsity_scale(step) * l1_loss

        if not logging:
            return total
        l2_loss = torch.linalg.norm(x - x_hat, dim=-1).mean()
        return LossLog(x, x_hat, features, {
            "l2_loss": l2_loss.item(),
            "mse_loss": recon_loss.item(),
            "sparsity_loss": l1_loss.item(),
            "loss": total.item(),
        })

    def update(self, step: int, activations: torch.Tensor) -> float:
        activations = activations.to(self.device)
        self.optimizer.zero_grad()
        loss = self.loss(activations, step=step)
        loss.backward()
        self.optimizer.step()
        self.scheduler.step()
        return loss.item()

    @property
    def config(self) -> dict:
        return {
            "trainer_class": "StandardTrainer",
            "dict_class": "AutoEncoder",
            "activation_dim": self.ae.activation_dim,
            "dict_size": self.ae.dict_size,
            "lr": self.lr,
            "l1_penalty": self.l1_penalty,
            "warmup_steps": self.warmup_steps,
            "sparsity_warmup_steps": self.sparsity_warmup_steps,
            "decay_start": self.decay_start,
            "steps": self.steps,
            "seed": self.seed,
            "device": self.device,
            "layer": self.layer,
            "lm_name": self.lm_name,
            "wandb_name": self.wandb_name,
            "submodule_name": self.submodule_name,
        }
