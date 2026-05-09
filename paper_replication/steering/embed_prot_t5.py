"""Generate mean-pooled ProtT5 embeddings for sequences in a FASTA file.

Produces an h5 file keyed by sequence header (everything after '>'),
with each value a float32 array of shape (1024,).

Usage:
    python embed_prot_t5.py --fasta outputs/steering/sweep/sequences.fasta \
                            --out_h5 outputs/steering/sweep/embeddings.h5
"""
import re
from pathlib import Path

import click
import h5py
import numpy as np
import torch
from transformers import T5EncoderModel, T5Tokenizer


_MODEL_NAME = "Rostlab/prot_t5_xl_half_uniref50-enc"
_BATCH_SIZE = 8


@click.command()
@click.option("--fasta", required=True, type=click.Path(exists=True))
@click.option("--out_h5", required=True, type=click.Path())
def main(fasta: str, out_h5: str) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")

    tokenizer, model = _load_model(device)
    sequences = _read_fasta(Path(fasta))
    print(f"embedding {len(sequences)} sequences")

    Path(out_h5).parent.mkdir(parents=True, exist_ok=True)
    keys = list(sequences.keys())
    with h5py.File(out_h5, "w") as h5f:
        for i in range(0, len(keys), _BATCH_SIZE):
            batch_keys = keys[i: i + _BATCH_SIZE]
            batch_seqs = [sequences[k] for k in batch_keys]
            embeddings = _embed_batch(tokenizer, model, batch_seqs, device)
            for key, emb in zip(batch_keys, embeddings):
                h5f.create_dataset(key, data=emb)
            print(f"  {min(i + _BATCH_SIZE, len(keys))}/{len(keys)}")

    print(f"wrote {out_h5}")


def _load_model(device: torch.device) -> tuple:
    print(f"loading {_MODEL_NAME}...")
    tokenizer = T5Tokenizer.from_pretrained(_MODEL_NAME, do_lower_case=False)
    model = T5EncoderModel.from_pretrained(_MODEL_NAME, torch_dtype=torch.float16)
    model = model.to(device).eval()
    return tokenizer, model


def _embed_batch(
    tokenizer: T5Tokenizer,
    model: T5EncoderModel,
    sequences: list[str],
    device: torch.device,
) -> list[np.ndarray]:
    spaced = [" ".join(list(re.sub(r"[UZOB]", "X", s))) for s in sequences]
    enc = tokenizer(spaced, return_tensors="pt", padding=True, truncation=True, max_length=1024)
    enc = {k: v.to(device) for k, v in enc.items()}
    with torch.no_grad():
        out = model(**enc)
    hidden = out.last_hidden_state.float()  # (B, L+1, 1024)
    mask = enc["attention_mask"].unsqueeze(-1).float()
    # mean-pool over non-padding tokens (exclude EOS)
    seq_lens = mask.sum(dim=1) - 1  # subtract EOS token
    summed = (hidden * mask)[:, :-1].sum(dim=1)
    mean_embs = (summed / seq_lens).cpu().numpy().astype(np.float32)
    return [mean_embs[i] for i in range(len(sequences))]


def _read_fasta(path: Path) -> dict[str, str]:
    sequences: dict[str, str] = {}
    key = None
    seq_parts: list[str] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if key is not None:
                    sequences[key] = "".join(seq_parts)
                key = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line)
    if key is not None:
        sequences[key] = "".join(seq_parts)
    return sequences


if __name__ == "__main__":
    main()
