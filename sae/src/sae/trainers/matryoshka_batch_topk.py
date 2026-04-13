from collections import namedtuple
from math import isclose
from typing import Optional

import torch

from sae.models.matryoshka_batch_topk import MatryoshkaBatchTopKSAE
from sae.ops import (
    remove_gradient_parallel_to_decoder_directions,
    set_decoder_norm_to_unit_norm,
)
from sae.trainers._common import geometric_median, get_lr_schedule
from sae.trainers._matryoshka_helpers import (
    auxk_loss,
    build_group_sizes,
    nested_reconstruction_loss,
    update_threshold,
)
from sae.trainers.base import SAETrainer


LossLog = namedtuple("LossLog", ["x", "x_hat", "f", "losses"])


class MatryoshkaBatchTopKTrainer(SAETrainer):
    """Batch-TopK SAE trainer with Matryoshka nested group losses."""

    def __init__(
        self,
        steps: int,
        activation_dim: int,
        dict_size: int,
        k: int,
        layer: int,
        lm_name: str,
        group_fractions: list[float],
        group_weights: Optional[list[float]] = None,
        lr: Optional[float] = None,
        auxk_alpha: float = 1 / 32,
        warmup_steps: int = 1000,
        decay_start: Optional[int] = None,
        threshold_beta: float = 0.999,
        threshold_start_step: int = 1000,
        seed: Optional[int] = None,
        device: Optional[str] = None,
        wandb_name: str = "MatryoshkaBatchTopK",
        submodule_name: Optional[str] = None,
    ):
        super().__init__(seed)
        if seed is not None:
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)

        assert isclose(sum(group_fractions), 1.0)
        group_sizes = build_group_sizes(group_fractions, dict_size)
        if group_weights is None:
            group_weights = [1.0 / len(group_sizes)] * len(group_sizes)
        assert len(group_sizes) == len(group_weights)

        self.steps, self.layer, self.lm_name, self.submodule_name = steps, layer, lm_name, submodule_name
        self.wandb_name, self.k, self.auxk_alpha = wandb_name, k, auxk_alpha
        self.warmup_steps, self.decay_start = warmup_steps, decay_start
        self.threshold_beta, self.threshold_start_step = threshold_beta, threshold_start_step
        self.group_fractions, self.group_sizes, self.group_weights = group_fractions, group_sizes, group_weights
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.ae = MatryoshkaBatchTopKSAE(activation_dim, dict_size, k, group_sizes).to(self.device)

        self.lr = lr if lr is not None else 2e-4 / (dict_size / 2**14) ** 0.5
        self.top_k_aux = activation_dim // 2
        self.dead_feature_threshold = 10_000_000
        self.num_tokens_since_fired = torch.zeros(dict_size, dtype=torch.long, device=self.device)

        self.optimizer = torch.optim.Adam(self.ae.parameters(), lr=self.lr, betas=(0.9, 0.999))
        self.scheduler = torch.optim.lr_scheduler.LambdaLR(
            self.optimizer, lr_lambda=get_lr_schedule(steps, warmup_steps, decay_start)
        )
        self.logging_parameters = ["effective_l0", "dead_features", "pre_norm_auxk_loss"]
        self.effective_l0 = -1
        self.dead_features = -1
        self.pre_norm_auxk_loss = -1

    def loss(self, x: torch.Tensor, step: int, logging: bool = False):
        features, active_mask, post_relu = self.ae.encode(x, return_active=True, use_threshold=False)
        if step > self.threshold_start_step:
            update_threshold(self.ae.threshold, features, self.threshold_beta)

        reconstruction, l2_losses, mean_l2 = nested_reconstruction_loss(
            x, features, self.ae.b_dec, self.ae.W_dec,
            self.ae.group_sizes.tolist(), self.group_weights, self.ae.active_groups,
        )

        self.effective_l0 = self.k
        self.num_tokens_since_fired += x.size(0)
        self.num_tokens_since_fired[active_mask] = 0

        auxk, self.dead_features, self.pre_norm_auxk_loss = auxk_loss(
            (x - reconstruction).detach(),
            post_relu,
            self.ae.W_dec,
            self.num_tokens_since_fired,
            self.dead_feature_threshold,
            self.top_k_aux,
        )
        total = mean_l2 + self.auxk_alpha * auxk

        if not logging:
            return total
        losses = {"l2_loss": mean_l2.item(), "auxk_loss": auxk.item(), "loss": total.item(),
                  "min_l2_loss": l2_losses.min().item(), "max_l2_loss": l2_losses.max().item()}
        return LossLog(x, reconstruction, features, losses)

    def update(self, step: int, activations: torch.Tensor) -> float:
        activations = activations.to(self.device)
        if step == 0:
            self.ae.b_dec.data = geometric_median(activations)

        loss = self.loss(activations, step=step)
        loss.backward()

        self.ae.W_dec.grad = remove_gradient_parallel_to_decoder_directions(
            self.ae.W_dec.T, self.ae.W_dec.grad.T, self.ae.activation_dim, self.ae.dict_size
        ).T
        torch.nn.utils.clip_grad_norm_(self.ae.parameters(), 1.0)
        self.optimizer.step()
        self.optimizer.zero_grad()
        self.scheduler.step()

        self.ae.W_dec.data = set_decoder_norm_to_unit_norm(
            self.ae.W_dec.T, self.ae.activation_dim, self.ae.dict_size
        ).T
        return loss.item()

    @property
    def config(self) -> dict:
        fields = (
            "lr auxk_alpha warmup_steps decay_start threshold_beta threshold_start_step "
            "group_fractions group_weights group_sizes steps seed device layer lm_name "
            "wandb_name submodule_name"
        ).split()
        return {
            "trainer_class": "MatryoshkaBatchTopKTrainer",
            "dict_class": "MatryoshkaBatchTopKSAE",
            "activation_dim": self.ae.activation_dim,
            "dict_size": self.ae.dict_size,
            "k": self.ae.k.item(),
            **{f: getattr(self, f) for f in fields},
        }
