import torch
import torch.nn as nn

from sae.ops import set_decoder_norm_to_unit_norm


class MatryoshkaBatchTopKSAE(nn.Module):
    """Batch-TopK SAE with Matryoshka group structure (Bussman et al. 2024)."""

    def __init__(
        self,
        activation_dim: int,
        dict_size: int,
        k: int,
        group_sizes: list[int],
    ):
        super().__init__()
        assert sum(group_sizes) == dict_size
        assert all(s > 0 for s in group_sizes)
        assert isinstance(k, int) and k > 0

        self.activation_dim = activation_dim
        self.dict_size = dict_size

        self.register_buffer("k", torch.tensor(k, dtype=torch.int))
        self.register_buffer("threshold", torch.tensor(-1.0, dtype=torch.float32))
        self.register_buffer("group_sizes", torch.tensor(group_sizes))

        self.active_groups = len(group_sizes)
        self.group_indices = [0] + torch.cumsum(torch.tensor(group_sizes), 0).tolist()

        self.W_enc = nn.Parameter(torch.empty(activation_dim, dict_size))
        self.b_enc = nn.Parameter(torch.zeros(dict_size))
        self.W_dec = nn.Parameter(
            nn.init.kaiming_uniform_(torch.empty(dict_size, activation_dim))
        )
        self.b_dec = nn.Parameter(torch.zeros(activation_dim))

        self.W_dec.data = set_decoder_norm_to_unit_norm(
            self.W_dec.data.T, activation_dim, dict_size
        ).T
        self.W_enc.data = self.W_dec.data.clone().T

    def encode(
        self,
        x: torch.Tensor,
        return_active: bool = False,
        use_threshold: bool = True,
    ):
        post_relu = nn.functional.relu((x - self.b_dec) @ self.W_enc + self.b_enc)

        if use_threshold:
            encoded = post_relu * (post_relu > self.threshold)
        else:
            flat = post_relu.flatten()
            topk = flat.topk(self.k * x.size(0), sorted=False, dim=-1)
            encoded = (
                torch.zeros_like(flat)
                .scatter_(-1, topk.indices, topk.values)
                .reshape(post_relu.shape)
            )

        max_index = self.group_indices[self.active_groups]
        encoded[:, max_index:] = 0

        if return_active:
            return encoded, encoded.sum(0) > 0, post_relu
        return encoded

    def decode(self, f: torch.Tensor) -> torch.Tensor:
        return f @ self.W_dec + self.b_dec

    def forward(self, x: torch.Tensor, output_features: bool = False):
        features = self.encode(x)
        reconstruction = self.decode(features)
        if output_features:
            return reconstruction, features
        return reconstruction

    @torch.no_grad()
    def scale_biases(self, scale: float):
        self.b_enc.data *= scale
        self.b_dec.data *= scale
        if self.threshold >= 0:
            self.threshold *= scale

    @classmethod
    def from_pretrained(
        cls, path: str, k: int | None = None, device: str | None = None
    ) -> "MatryoshkaBatchTopKSAE":
        state_dict = torch.load(path, map_location="cpu")
        if "ae" in state_dict:
            state_dict = state_dict["ae"]
        activation_dim, dict_size = state_dict["W_enc"].shape
        if k is None:
            k = state_dict["k"].item()
        group_sizes = state_dict["group_sizes"].tolist()
        model = cls(activation_dim, dict_size, k=k, group_sizes=group_sizes)
        model.load_state_dict(state_dict)
        if device is not None:
            model.to(device)
        return model
