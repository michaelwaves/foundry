import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import h5py
import numpy as np
import torch


@dataclass
class DesignActivations:
    """All activations for one design, stacked with provenance retained."""

    design_id: str
    activations: torch.Tensor  # (n_samples, n_steps, n_tokens, activation_dim)
    atom_array: object
    feats: dict
    input_pdb_path: str
    generated_pdb_paths: list[str]  # one per sample (model_0..model_{n_samples-1})
    n_samples: int
    n_steps: int
    n_tokens: int

    def flat_tokens(self) -> torch.Tensor:
        n_samples, n_steps, n_tokens, channels = self.activations.shape
        return self.activations.reshape(n_samples * n_steps * n_tokens, channels)


def iter_design_activations(
    activations_path: str, hook_name: str, metadata_dir: str
) -> Iterator[DesignActivations]:
    """Yield per-design activations with metadata attached."""
    with h5py.File(activations_path, "r") as f:
        if hook_name not in f:
            raise KeyError(f"hook '{hook_name}' not in {list(f.keys())}")
        hook_group = f[hook_name]
        for design_id in hook_group.keys():
            yield _load_design(hook_group, design_id, metadata_dir)


def _load_design(hook_group, design_id: str, metadata_dir: str) -> DesignActivations:
    design_group = hook_group[design_id]
    step_ids = sorted(design_group.keys(), key=int)
    step_arrays = [design_group[step_id][...] for step_id in step_ids]
    stacked = np.stack(step_arrays, axis=1)  # (n_samples, n_steps, n_tokens, dim)

    metadata = _load_metadata(metadata_dir, design_id)
    n_samples = stacked.shape[0]
    return DesignActivations(
        design_id=design_id,
        activations=torch.from_numpy(stacked),
        atom_array=metadata["atom_array"],
        feats=metadata["feats"],
        input_pdb_path=metadata["specification"]["input"],
        generated_pdb_paths=_find_generated_pdbs(metadata_dir, design_id, n_samples),
        n_samples=n_samples,
        n_steps=stacked.shape[1],
        n_tokens=stacked.shape[2],
    )


def _load_metadata(metadata_dir: str, design_id: str) -> dict:
    path = Path(metadata_dir) / f"{design_id}_metadata.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)


def _find_generated_pdbs(metadata_dir: str, design_id: str, n_samples: int) -> list[str]:
    """Generated structures from RFD3 are dumped as <design_id>_model_<k>.cif.gz,
    where k is the diffusion batch index — same axis as activation sample dim.
    Train layout colocates them with metadata; test layout puts them in the parent."""
    search_roots = [Path(metadata_dir), Path(metadata_dir).parent]
    paths = []
    for k in range(n_samples):
        filename = f"{design_id}_model_{k}.cif.gz"
        match = next((root / filename for root in search_roots if (root / filename).exists()), None)
        if match is None:
            raise FileNotFoundError(
                f"missing generated structure {filename} in {[str(r) for r in search_roots]}"
            )
        paths.append(str(match))
    return paths
