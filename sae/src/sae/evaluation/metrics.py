from dataclasses import dataclass

import torch


@dataclass
class Metrics:
    frac_variance_explained: float
    cossim: float
    l2_ratio: float
    l0: float
    l1: float
    l2_loss: float
    relative_reconstruction_bias: float
    frac_alive: float
    n_tokens: int


@torch.no_grad()
def compute_metrics(
    sae: torch.nn.Module, tokens: torch.Tensor, batch_size: int = 4096
) -> Metrics:
    """Stream-compute standard SAE metrics over a (N, D) token matrix."""
    sae.eval()
    device = next(sae.parameters()).device

    accumulators = _ZeroAccumulators(sae.dict_size, device)
    for batch in tokens.split(batch_size):
        batch = batch.to(device=device, dtype=torch.float32)
        reconstruction, features = sae(batch, output_features=True)
        _accumulate_batch(accumulators, batch, reconstruction, features)

    n = accumulators.n_tokens
    return Metrics(
        frac_variance_explained=1 - accumulators.residual_var_sum / (accumulators.total_var_sum + 1e-12),
        cossim=accumulators.cossim_sum / n,
        l2_ratio=accumulators.l2_ratio_sum / n,
        l0=accumulators.l0_sum / n,
        l1=accumulators.l1_sum / n,
        l2_loss=accumulators.l2_loss_sum / n,
        relative_reconstruction_bias=accumulators.bias_num_sum / (accumulators.bias_denom_sum + 1e-12),
        frac_alive=(accumulators.feature_fire_count > 0).float().mean().item(),
        n_tokens=n,
    )


class _ZeroAccumulators:
    def __init__(self, dict_size: int, device: torch.device):
        self.n_tokens = 0
        self.l0_sum = 0.0
        self.l1_sum = 0.0
        self.l2_loss_sum = 0.0
        self.cossim_sum = 0.0
        self.l2_ratio_sum = 0.0
        self.bias_num_sum = 0.0
        self.bias_denom_sum = 0.0
        self.total_var_sum = 0.0
        self.residual_var_sum = 0.0
        self.feature_fire_count = torch.zeros(dict_size, device=device)


def _accumulate_batch(acc: _ZeroAccumulators, x: torch.Tensor, x_hat: torch.Tensor, features: torch.Tensor) -> None:
    batch_size = x.shape[0]
    acc.n_tokens += batch_size
    residual = x - x_hat
    acc.l2_loss_sum += residual.norm(dim=-1).sum().item()
    acc.l0_sum += (features != 0).float().sum(dim=-1).sum().item()
    acc.l1_sum += features.norm(p=1, dim=-1).sum().item()

    x_normed = x / (x.norm(dim=-1, keepdim=True) + 1e-8)
    x_hat_normed = x_hat / (x_hat.norm(dim=-1, keepdim=True) + 1e-8)
    acc.cossim_sum += (x_normed * x_hat_normed).sum(dim=-1).sum().item()
    acc.l2_ratio_sum += (x_hat.norm(dim=-1) / (x.norm(dim=-1) + 1e-8)).sum().item()

    acc.bias_num_sum += x_hat.norm(dim=-1).pow(2).sum().item()
    acc.bias_denom_sum += (x * x_hat).sum().item()

    acc.total_var_sum += x.var(dim=0, unbiased=False).sum().item() * batch_size
    acc.residual_var_sum += residual.var(dim=0, unbiased=False).sum().item() * batch_size

    acc.feature_fire_count += (features != 0).float().sum(dim=0)
