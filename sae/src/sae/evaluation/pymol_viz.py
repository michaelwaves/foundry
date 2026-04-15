import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ResidueHit:
    chain_id: str
    res_id: int
    activation: float


def render_feature_on_structure(
    design_id: str,
    feature_id: int,
    pdb_path: str,
    token_hits: list[tuple[int, float]],
    atom_array,
    output_dir: Path,
) -> Path:
    """Write a .pml script highlighting residues where the feature fires; render PNG if pymol found."""
    residues = _tokens_to_residues(token_hits, atom_array)
    script_path = output_dir / f"{design_id}_feature_{feature_id}.pml"
    image_path = output_dir / f"{design_id}_feature_{feature_id}.png"
    write_pymol_script(pdb_path, residues, script_path, image_path)
    _try_render(script_path)
    return script_path


def write_pymol_script(
    pdb_path: str,
    residues: list[ResidueHit],
    script_path: Path,
    image_path: Path,
) -> None:
    script_path.parent.mkdir(parents=True, exist_ok=True)
    with open(script_path, "w") as f:
        f.write(_build_script(pdb_path, residues, image_path))


def _build_script(pdb_path: str, residues: list[ResidueHit], image_path: Path) -> str:
    lines = [
        f"load {pdb_path}, structure",
        "bg_color white",
        "hide everything",
        "show cartoon, structure",
        "show sticks, hetatm",
        "color gray70, structure",
    ]
    max_activation = max((r.activation for r in residues), default=1.0) or 1.0
    hit_selections: list[str] = []
    for index, hit in enumerate(residues):
        intensity = hit.activation / max_activation
        color = f"feature_color_{index}"
        red, green, blue = _heat_rgb(intensity)
        selection = f"feature_{index}"
        hit_selections.append(selection)
        lines += [
            f"set_color {color}, [{red:.3f}, {green:.3f}, {blue:.3f}]",
            f"select {selection}, chain {hit.chain_id} and resi {hit.res_id}",
            f"color {color}, {selection}",
            f"show sticks, {selection}",
        ]
    zoom_target = " or ".join(hit_selections) if hit_selections else "structure"
    lines += [
        "orient",
        f"zoom ({zoom_target}), 8",
        "ray 1200, 900",
        f"png {image_path}, dpi=150",
    ]
    return "\n".join(lines) + "\n"


def _tokens_to_residues(token_hits: list[tuple[int, float]], atom_array) -> list[ResidueHit]:
    residues: list[ResidueHit] = []
    for token_id, activation in token_hits:
        mask = atom_array.token_id == token_id
        if not mask.any():
            continue
        chain_id = str(atom_array.chain_id[mask][0])
        res_id = int(atom_array.res_id[mask][0])
        residues.append(ResidueHit(chain_id=chain_id, res_id=res_id, activation=float(activation)))
    return residues


def _heat_rgb(intensity: float) -> tuple[float, float, float]:
    intensity = float(np.clip(intensity, 0.0, 1.0))
    return (1.0, 1.0 - intensity, 0.1 * (1 - intensity))


def _try_render(script_path: Path) -> None:
    pymol = shutil.which("pymol")
    if pymol is None:
        return
    subprocess.run([pymol, "-cq", str(script_path)], check=False)
