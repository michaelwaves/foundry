import torch
import torch.nn as nn


class AutoEncoder(nn.Module):
    """Single-layer ReLU SAE from 'Towards Monosemanticity'."""

    def __init__(self, activation_dim: int, dict_size: int):
        super().__init__()
        self.activation_dim = activation_dim
        self.dict_size = dict_size

        self.bias = nn.Parameter(torch.zeros(activation_dim))
        self.encoder = nn.Linear(activation_dim, dict_size, bias=True)
        self.decoder = nn.Linear(dict_size, activation_dim, bias=False)

        weights = torch.randn(activation_dim, dict_size)
        weights = weights / weights.norm(dim=0, keepdim=True) * 0.1
        self.encoder.weight = nn.Parameter(weights.clone().T)
        self.decoder.weight = nn.Parameter(weights.clone())

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return nn.functional.relu(self.encoder(x - self.bias))

    def decode(self, f: torch.Tensor) -> torch.Tensor:
        return self.decoder(f) + self.bias

    def forward(self, x: torch.Tensor, output_features: bool = False):
        features = self.encode(x)
        reconstruction = self.decode(features)
        if output_features:
            return reconstruction, features
        return reconstruction

    @classmethod
    def from_pretrained(cls, path: str, device: str | None = None) -> "AutoEncoder":
        state_dict = torch.load(path, map_location="cpu")
        if "ae" in state_dict:
            state_dict = state_dict["ae"]
        activation_dim, dict_size = state_dict["encoder.weight"].shape[1], state_dict["encoder.weight"].shape[0]
        model = cls(activation_dim, dict_size)
        model.load_state_dict(state_dict)
        if device is not None:
            model.to(device)
        return model
