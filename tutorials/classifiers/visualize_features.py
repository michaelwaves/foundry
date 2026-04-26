#!/usr/bin/env python3
"""Render PyMOL scripts (and PNGs if pymol is on PATH) showing where chosen SAE
features fire on RFD3-generated structures.

Bypasses sae.evaluation.iter_design_activations because the rfd3_partial
collection didn't dump _metadata.pkl files — we read residue ordering directly
from the .cif.gz that saffron collect saved next to each design.

Usage:
  python visualize_features.py \
      --checkpoint outputs/sae/2026-04-26_15-38-55/train/block12/final.pt \
      --activations tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5 \
      --metadata-dir tutorials/sae_data_rfd3_partial/train_activations \
      --hook block12 \
      --features 123,307 \
      --top-designs 3 \
      --top-residues 5 \
      --out outputs/classifiers/viz/rfd3_block12
"""
import argparse
import gzip
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import torch
from biotite.structure.io.pdbx import CIFFile, get_structure

from detectors.features.sae_encode import SAEEncodeExtractor


@dataclass
class TokenHit:
    chain_id: str
    res_id: int
    activation: float


def main() -> None:
    args = _parse_args()
    feature_ids = [int(x) for x in args.features.split(",")]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    extractor = SAEEncodeExtractor.from_checkpoint(args.checkpoint, device=args.device)
    feature_max_per_design = _scan_designs(args.activations, args.hook, extractor, feature_ids)

    for feature_id in feature_ids:
        ranked = sorted(feature_max_per_design[feature_id], key=lambda r: -r[2])[: args.top_designs]
        for design_id, sample_idx, max_activation, top_tokens in ranked:
            cif_path = _find_cif(args.metadata_dir, design_id, sample_idx)
            residues = _tokens_to_residues(cif_path, top_tokens, args.top_residues)
            stem = f"feature_{feature_id:05d}__{design_id}__model_{sample_idx}"
            _write_pml(out_dir / f"{stem}.pml", cif_path, residues, out_dir / f"{stem}.png")
            print(f"feature {feature_id} @ {design_id} model_{sample_idx}: max={max_activation:.3f} -> {stem}.pml")
    print(f"\nwrote .pml scripts to {out_dir}; render with: pymol -cq <file>.pml")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--activations", required=True)
    parser.add_argument("--metadata-dir", required=True,
                        help="dir with <design_id>_model_<k>.cif.gz files")
    parser.add_argument("--hook", required=True)
    parser.add_argument("--features", required=True, help="comma-separated feature ids")
    parser.add_argument("--top-designs", type=int, default=3,
                        help="render the N highest-activating (design, sample) pairs per feature")
    parser.add_argument("--top-residues", type=int, default=5,
                        help="highlight the K strongest-firing residues per render")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def _scan_designs(activations_path: str, hook: str, extractor, feature_ids: list[int]):
    """Return {feature_id: [(design_id, sample_idx, max_activation, [(token_idx, act), ...])]}."""
    out = {fid: [] for fid in feature_ids}
    feature_index = torch.tensor(feature_ids, dtype=torch.long)
    with h5py.File(activations_path, "r") as f:
        for design_id in f[hook].keys():
            steps = sorted(f[hook][design_id].keys(), key=int)
            arr = np.stack([f[hook][design_id][s][...] for s in steps], axis=1)  # (n_s, n_step, n_tok, dim)
            encoded = extractor.transform(torch.from_numpy(arr).float())  # (n_s, n_step, n_tok, F)
            mean_over_steps = encoded.mean(dim=1)  # (n_s, n_tok, F)
            slab = mean_over_steps.index_select(-1, feature_index)  # (n_s, n_tok, len(feature_ids))
            for col, feature_id in enumerate(feature_ids):
                tokenwise = slab[..., col]  # (n_s, n_tok)
                for sample_idx in range(tokenwise.shape[0]):
                    activations = tokenwise[sample_idx]
                    if activations.max().item() <= 0:
                        continue
                    top_indices = activations.topk(min(8, activations.numel())).indices.tolist()
                    top_tokens = [(int(t), float(activations[t])) for t in top_indices if activations[t] > 0]
                    out[feature_id].append(
                        (design_id, sample_idx, float(activations.max().item()), top_tokens)
                    )
    return out


def _find_cif(metadata_dir: str, design_id: str, sample_idx: int) -> Path:
    candidates = [Path(metadata_dir) / f"{design_id}_model_{sample_idx}.cif.gz",
                  Path(metadata_dir).parent / f"{design_id}_model_{sample_idx}.cif.gz"]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"no cif.gz for {design_id} model_{sample_idx}")


def _tokens_to_residues(cif_path: Path, token_hits: list[tuple[int, float]], top_k: int) -> list[TokenHit]:
    with gzip.open(cif_path, "rt") as f:
        cif = CIFFile.read(f)
    structure = get_structure(cif, model=1)
    ca_atoms = structure[structure.atom_name == "CA"]
    chain_ids = list(ca_atoms.chain_id)
    res_ids = list(ca_atoms.res_id)
    hits = []
    for token_idx, activation in sorted(token_hits, key=lambda h: -h[1])[:top_k]:
        if 0 <= token_idx < len(chain_ids):
            hits.append(TokenHit(chain_id=str(chain_ids[token_idx]),
                                 res_id=int(res_ids[token_idx]),
                                 activation=float(activation)))
    return hits


def _write_pml(script_path: Path, cif_path: Path, residues: list[TokenHit], image_path: Path) -> None:
    max_activation = max((r.activation for r in residues), default=1.0) or 1.0
    lines = [
        f"load {cif_path}, structure",
        "bg_color white", "hide everything", "show cartoon, structure",
        "color gray70, structure",
    ]
    selections = []
    for index, hit in enumerate(residues):
        intensity = hit.activation / max_activation
        red, green, blue = 1.0, 1.0 - intensity, 0.1 * (1 - intensity)
        sel = f"hit_{index}"
        selections.append(sel)
        lines += [
            f"set_color color_{index}, [{red:.3f}, {green:.3f}, {blue:.3f}]",
            f"select {sel}, chain {hit.chain_id} and resi {hit.res_id}",
            f"color color_{index}, {sel}",
            f"show sticks, {sel}",
        ]
    target = " or ".join(selections) if selections else "structure"
    lines += ["orient", f"zoom ({target}), 8", "ray 1200, 900", f"png {image_path}, dpi=150"]
    script_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
