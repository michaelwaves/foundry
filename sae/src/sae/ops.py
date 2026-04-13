import einops
import torch


@torch.no_grad()
def set_decoder_norm_to_unit_norm(
    W_dec: torch.Tensor, activation_dim: int, dict_size: int
) -> torch.Tensor:
    """Normalize decoder columns to unit length in-place. W_dec has shape (activation_dim, dict_size)."""
    assert W_dec.shape == (activation_dim, dict_size)
    eps = torch.finfo(W_dec.dtype).eps
    W_dec /= W_dec.norm(dim=0, keepdim=True) + eps
    return W_dec


@torch.no_grad()
def remove_gradient_parallel_to_decoder_directions(
    W_dec: torch.Tensor, W_dec_grad: torch.Tensor, activation_dim: int, dict_size: int
) -> torch.Tensor:
    assert W_dec.shape == (activation_dim, dict_size)
    normed = W_dec / (W_dec.norm(dim=0, keepdim=True) + 1e-6)
    parallel = einops.einsum(W_dec_grad, normed, "d f, d f -> f")
    W_dec_grad -= einops.einsum(parallel, normed, "f, d f -> d f")
    return W_dec_grad
