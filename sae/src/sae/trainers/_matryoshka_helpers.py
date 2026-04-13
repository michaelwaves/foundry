import torch


def auxk_loss(
    residual: torch.Tensor,
    post_relu: torch.Tensor,
    W_dec: torch.Tensor,
    num_tokens_since_fired: torch.Tensor,
    dead_feature_threshold: int,
    top_k_aux: int,
) -> tuple[torch.Tensor, int, float]:
    """Loss on top-k dead features to resurrect them. Returns (loss, n_dead, pre_norm_loss)."""
    dead_mask = num_tokens_since_fired >= dead_feature_threshold
    n_dead = int(dead_mask.sum())
    if n_dead == 0:
        zero = torch.tensor(0.0, device=residual.device, dtype=residual.dtype)
        return zero, 0, -1

    k_aux = min(top_k_aux, n_dead)
    dead_acts = torch.where(dead_mask[None], post_relu, -torch.inf)
    aux_vals, aux_idx = dead_acts.topk(k_aux, sorted=False)
    aux_acts = torch.zeros_like(post_relu).scatter_(-1, aux_idx, aux_vals)

    reconstruction = aux_acts @ W_dec
    numerator = (residual.float() - reconstruction.float()).pow(2).sum(dim=-1).mean()
    residual_mu = residual.mean(dim=0, keepdim=True).expand_as(residual)
    denominator = (residual.float() - residual_mu.float()).pow(2).sum(dim=-1).mean()
    return (numerator / denominator).nan_to_num(0.0), n_dead, numerator.item()


def update_threshold(
    threshold: torch.Tensor, features: torch.Tensor, beta: float
) -> None:
    device_type = "cuda" if features.is_cuda else "cpu"
    with torch.autocast(device_type=device_type, enabled=False), torch.no_grad():
        active = features[features > 0]
        min_activation = (
            active.min().detach().to(torch.float32)
            if active.numel() > 0
            else torch.tensor(0.0)
        )
        if threshold < 0:
            threshold.copy_(min_activation)
        else:
            threshold.copy_(beta * threshold + (1 - beta) * min_activation)


def build_group_sizes(group_fractions: list[float], dict_size: int) -> list[int]:
    sizes = [int(f * dict_size) for f in group_fractions[:-1]]
    sizes.append(dict_size - sum(sizes))
    return sizes


def nested_reconstruction_loss(
    x: torch.Tensor,
    features: torch.Tensor,
    b_dec: torch.Tensor,
    W_dec: torch.Tensor,
    group_sizes: list[int],
    group_weights: list[float],
    active_groups: int,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Returns (final reconstruction, stacked per-group l2 losses, mean_l2)."""
    reconstruction = torch.zeros_like(x) + b_dec
    W_dec_chunks = torch.split(W_dec, group_sizes, dim=0)
    f_chunks = torch.split(features, group_sizes, dim=1)

    losses = []
    for i in range(active_groups):
        reconstruction = reconstruction + f_chunks[i] @ W_dec_chunks[i]
        losses.append(
            (x - reconstruction).pow(2).sum(dim=-1).mean() * group_weights[i]
        )
    stacked = torch.stack(losses)
    return reconstruction, stacked, stacked.mean()
