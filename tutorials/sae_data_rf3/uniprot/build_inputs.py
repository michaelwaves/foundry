#!/usr/bin/env python3
"""Build/refresh an RF3 saffron-collect inputs JSON from a sources.csv that
points at PDB structures (same format used by sae_data_rfd3_partial). Each row
becomes one folding example whose sequence is extracted from chain A of the PDB
and whose `name` is preserved verbatim — so design_ids match the RFD3 partial
collection on the same sources.csv, enabling cross-model probing on shared labels.

Output JSON shape (mirrors the RF3 `build_inputs.py` in the parent folder)::

    {
        "run_config": {"activation_collection": {"hooks": [...]}},
        "examples": [
            {"name": "<row.name>", "components": [{"seq": "...", "chain_id": "A"}]},
            ...
        ],
    }

`run_config` is preserved across rebuilds; on first run it's seeded from
`hooks.yaml` (defaults to `../hooks.yaml`, the RF3 hooks the SAEs were trained on).

Usage:
  python build_inputs.py --sources <sources.csv> --out train_inputs.json
"""
import argparse
import csv
import json
import random
from pathlib import Path

import yaml


def main() -> None:
    args = _parse_args()
    rng = random.Random(args.seed)

    rows = list(_read_sources(Path(args.sources)))
    if args.subsample is not None and args.subsample < len(rows):
        rows = rng.sample(rows, args.subsample)

    examples, skipped = _build_examples(rows)
    run_config = _load_or_seed_run_config(Path(args.out), Path(args.hooks_yaml))

    payload = {"run_config": run_config, "examples": examples}
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"wrote {len(examples)} examples + run_config -> {args.out} (skipped {skipped})")


def _parse_args() -> argparse.Namespace:
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True,
                        help="CSV with columns: name, label, structure_path")
    parser.add_argument("--out", required=True)
    parser.add_argument("--subsample", type=int, default=None,
                        help="if set, randomly take this many rows from the sources CSV")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hooks-yaml", default=str(here.parent / "hooks.yaml"),
                        help="seed run_config from this file when out doesn't exist yet")
    return parser.parse_args()


def _read_sources(path: Path) -> list[dict]:
    with path.open() as f:
        return [row for row in csv.DictReader(f)
                if row.get("name") and row.get("structure_path")]


def _build_examples(rows: list[dict]) -> tuple[list[dict], int]:
    examples: list[dict] = []
    skipped = 0
    for row in rows:
        pdb_path = Path(row["structure_path"]).resolve()
        sequence = _extract_chain_sequence(pdb_path)
        if not sequence:
            print(f"skip {row['name']} ({pdb_path.name}): no chain-A residues")
            skipped += 1
            continue
        examples.append({
            "name": row["name"],
            "components": [{"seq": sequence, "chain_id": "A"}],
        })
    return examples, skipped


def _extract_chain_sequence(pdb_path: Path) -> str:
    seen: set[tuple[str, str]] = set()
    chain_id: str | None = None
    residues: list[str] = []
    with pdb_path.open() as fh:
        for line in fh:
            if not line.startswith("ATOM"):
                continue
            if line[12:16].strip() != "CA":
                continue
            res_name = line[17:20].strip()
            one_letter = _THREE_TO_ONE.get(res_name)
            if one_letter is None:
                continue
            chain = line[21]
            if chain_id is None:
                chain_id = chain
            if chain != chain_id:
                continue
            res_seq = line[22:27].strip()
            key = (chain, res_seq)
            if key in seen:
                continue
            seen.add(key)
            residues.append(one_letter)
    return "".join(residues)


def _load_or_seed_run_config(out_path: Path, hooks_yaml: Path) -> dict:
    if out_path.exists():
        existing = json.loads(out_path.read_text())
        if isinstance(existing, dict) and "run_config" in existing:
            return existing["run_config"]
    return {"activation_collection": yaml.safe_load(hooks_yaml.read_text())}


_THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


if __name__ == "__main__":
    main()
