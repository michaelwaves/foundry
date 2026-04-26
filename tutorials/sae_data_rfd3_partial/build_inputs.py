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
    for row in rows:
        # RFD3's input parser resolves relative `input` paths against the JSON's
        # directory, so a sources.csv with project-relative paths breaks the join.
        # Always emit absolute paths (resolved against CWD if the row was relative).
        payload[row["name"]] = {
            "input": str(Path(row["structure_path"]).resolve()),
            "partial_t": float(row.get("partial_t") or args.partial_t),
        }

    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"wrote {len(rows)} examples + run_config -> {args.out}")


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


if __name__ == "__main__":
    main()
