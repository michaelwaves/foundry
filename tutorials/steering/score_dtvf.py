"""Score sequences with DTVF and write per-design virulence probabilities.

Usage:
    python score_dtvf.py --embeddings outputs/steering/sweep/embeddings.h5 \
                         --out_csv    outputs/steering/sweep/dtvf_scores.csv
"""
from pathlib import Path

import click
import h5py
import numpy as np
import pandas as pd
import torch
import torch.nn as nn


# Model definitions must be in __main__ scope so torch.load can unpickle them.
class Attention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.linear = nn.Linear(hidden_size, hidden_size)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, lstm_out):
        out = self.linear(lstm_out)
        score = torch.bmm(out, out.transpose(1, 2))
        return torch.bmm(self.softmax(score), lstm_out)


class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_classes, drop):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.attention = Attention(hidden_size)
        self.batch_norm = nn.BatchNorm1d(hidden_size)
        self.fc = nn.Linear(hidden_size, num_classes)
        self.dropout = nn.Dropout(drop)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.attention(out)
        out = self.batch_norm(out.permute(0, 2, 1)).permute(0, 2, 1)
        return self.fc(out[:, -1, :])


class CNNModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, num_classes, drop):
        super().__init__()
        self.conv = nn.Conv1d(input_size, hidden_size, kernel_size=3, padding=1)
        self.attention = Attention(hidden_size)
        self.batch_norm = nn.BatchNorm1d(hidden_size)
        self.fc = nn.Linear(hidden_size, num_classes)
        self.dropout = nn.Dropout(drop)

    def forward(self, x):
        out = self.conv(x.permute(0, 2, 1)).permute(0, 2, 1)
        out = self.attention(out)
        out = self.batch_norm(out.permute(0, 2, 1)).permute(0, 2, 1)
        return self.fc(out[:, -1, :])


class DualModel(nn.Module):
    def __init__(self, input_size, hidden_size_cnn, hidden_size_lstm,
                 num_layers_cnn, num_layers_lstm, num_classes, drop_cnn, drop_lstm):
        super().__init__()
        self.cnn = CNNModel(input_size, hidden_size_cnn, num_layers_cnn, num_classes, drop_cnn)
        self.lstm = LSTMModel(input_size, hidden_size_lstm, num_layers_lstm, num_classes, drop_lstm)
        self.weight = nn.Parameter(torch.tensor(0.8))

    def forward(self, x):
        return self.weight * self.cnn(x) + (1 - self.weight) * self.lstm(x)


@click.command()
@click.option("--embeddings", required=True, type=click.Path(exists=True))
@click.option("--model_path", default="DTVF/best_model.pth", type=click.Path())
@click.option("--out_csv", required=True, type=click.Path())
def main(embeddings: str, model_path: str, out_csv: str) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = _load_model(Path(model_path), device)

    rows = []
    with h5py.File(embeddings, "r") as f:
        keys = list(f.keys())
        for key in keys:
            emb = f[key][()]  # (1024,)
            prob = _score(model, emb, device)
            design_id, alpha = _parse_key(key)
            rows.append({"design_id": design_id, "alpha": alpha, "virulence_prob": prob})

    df = pd.DataFrame(rows)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, na_rep="NA")
    print(df.groupby("alpha")["virulence_prob"].mean().sort_index().to_string())
    print(f"\nwrote {out_csv}")


def _load_model(model_path: Path, device: torch.device) -> nn.Module:
    model = torch.load(model_path, map_location=device, weights_only=False)
    model.eval()
    return model.to(device)


def _score(model: nn.Module, embedding: np.ndarray, device: torch.device) -> float:
    x = torch.tensor(embedding, dtype=torch.float32).reshape(1, 1, -1).to(device)
    with torch.no_grad():
        logit = model(x)
        prob = torch.sigmoid(logit)[0][1].item()
    return prob


def _parse_key(key: str) -> tuple[str, str]:
    # key format: "{design_id}|{alpha}"
    parts = key.rsplit("|", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (key, "unknown")


if __name__ == "__main__":
    main()
