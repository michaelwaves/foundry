#!/usr/bin/env python3
"""Build/refresh an RFD3 partial-diffusion saffron-collect inputs JSON.

Each entry sets `partial_t` (Å of noise) and points at a full PDB. RFD3 noises
the structure to that level and runs the reverse trajectory — activations
during the rebuild are conditioned on the source structure (cf. unconditional
generation, where they aren't).

Output JSON shape (mirrors RFD3's existing format)::

    {
        "run_config": {"activation_collection": {"hooks": [...]}},
        "<example_name>": {"input": "/path/to.pdb", "partial_t": 5.0},
        ...
    }

Sources are read from a CSV with columns: `name,label,structure_path[,partial_t]`.
The label is used downstream (detect labels) and ignored here.

Usage:
  python build_inputs.py \
      --sources sources.csv \
      --out train_inputs.json \
      --partial-t 5.0
"""
import argparse
import csv
import json
from pathlib import Path

import yaml


def main() -> None:
    args = _parse_args()
    rows = list(_read_sources(Path(args.sources)))
    run_config = _load_or_seed_run_config(Path(args.out), Path(args.hooks_yaml))

    payload = {"run_config": run_config}
    skipped = 0
    for row in rows:
        path = Path(row["structure_path"]).resolve()
        reason = _first_aa_missing_ca(path)
        if reason is not None:
            print(f"skip {row['name']} ({path.name}): {reason}")
            skipped += 1
            continue
        # RFD3's input parser resolves relative `input` paths against the JSON's
        # directory, so a sources.csv with project-relative paths breaks the join.
        # Always emit absolute paths (resolved against CWD if the row was relative).
        payload[row["name"]] = {
            "input": str(path),
            "partial_t": float(row.get("partial_t") or args.partial_t),
        }

    Path(args.out).write_text(json.dumps(payload, indent=2))
    kept = len(rows) - skipped
    print(f"wrote {kept} examples + run_config -> {args.out} (skipped {skipped})")


def _parse_args() -> argparse.Namespace:
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True,
                        help="CSV with columns: name, label, structure_path[, partial_t]")
    parser.add_argument("--out", required=True)
    parser.add_argument("--partial-t", type=float, default=5.0,
                        help="default partial_t (Å of noise) when not set in sources.csv. "
                             "Lower = closer to source structure; t<=15 recommended.")
    parser.add_argument("--hooks-yaml", default=str(here / "hooks.yaml"))
    return parser.parse_args()


def _read_sources(path: Path):
    with path.open() as f:
        for row in csv.DictReader(f):
            if not row.get("name") or not row.get("structure_path"):
                continue
            yield row


def _load_or_seed_run_config(out_path: Path, hooks_yaml: Path) -> dict:
    if out_path.exists():
        existing = json.loads(out_path.read_text())
        if isinstance(existing, dict) and "run_config" in existing:
            return existing["run_config"]
    return {"activation_collection": yaml.safe_load(hooks_yaml.read_text())}


# Standard amino acids — RFD3's pipeline expects each as one token with a CA
# representative. Non-paddable motif residues missing CA crash the encoder.
_STANDARD_AA = frozenset({
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
})


def _first_aa_missing_ca(pdb_path: Path) -> str | None:
    atoms_by_residue: dict[tuple[str, str, str], set[str]] = {}
    residue_order: list[tuple[str, str, str]] = []
    with pdb_path.open() as fh:
        for line in fh:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            res_name = line[17:20].strip()
            if res_name not in _STANDARD_AA:
                continue
            key = (line[21], line[22:27].strip(), res_name)
            if key not in atoms_by_residue:
                atoms_by_residue[key] = set()
                residue_order.append(key)
            atoms_by_residue[key].add(line[12:16].strip())
    for chain, res_seq, res_name in residue_order:
        atoms = atoms_by_residue[(chain, res_seq, res_name)]
        if "CA" not in atoms:
            return f"{res_name} {chain}{res_seq} missing CA (atoms: {sorted(atoms)})"
    return None


if __name__ == "__main__":
    main()
