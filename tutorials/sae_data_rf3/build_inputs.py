#!/usr/bin/env python3
"""Build/refresh an RF3 saffron-collect inputs JSON from ToxinPred CSVs.

The output JSON is a dict::

    {"run_config": {"activation_collection": {"hooks": [...]}}, "examples": [...]}

`run_config` is preserved when the file already exists (so hand-edited hook configs
survive a rebuild). On first run, `run_config` is seeded from `hooks.yaml`. The
`examples` list is always regenerated from the source CSVs.

Each example name is `{stem}_{lineno}` so it matches the source_id format emitted
by `detect labels` for line-format CSVs — `design_id == example_id == source_id`.

Usage:
  python build_inputs.py \
      --positive ../../detectors/datasets/toxinpred3/train_pos.csv \
      --negative ../../detectors/datasets/toxinpred3/train_neg.csv \
      --out train_inputs.json \
      --subsample 100
"""
import argparse
import json
import random
from pathlib import Path

import yaml


def main() -> None:
    args = _parse_args()
    rng = random.Random(args.seed)

    examples = _build_examples(args.positive + args.negative, rng, args.subsample)
    run_config = _load_or_seed_run_config(Path(args.out), Path(args.hooks_yaml))

    payload = {"run_config": run_config, "examples": examples}
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"wrote {len(examples)} examples + run_config -> {args.out}")


def _parse_args() -> argparse.Namespace:
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive", action="append", default=[])
    parser.add_argument("--negative", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--subsample", type=int, default=None,
                        help="if set, randomly take this many sequences from each file")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hooks-yaml", default=str(here / "hooks.yaml"),
                        help="seed run_config from this file when out doesn't exist yet")
    return parser.parse_args()


def _build_examples(paths: list[str], rng: random.Random, subsample: int | None) -> list[dict]:
    examples = []
    for path_str in paths:
        path = Path(path_str)
        sequences = _read_sequences(path)
        if subsample is not None and subsample < len(sequences):
            sequences = rng.sample(sequences, subsample)
        for lineno, seq in sequences:
            examples.append({
                "name": f"{path.stem}_{lineno}",
                "components": [{"seq": seq, "chain_id": "A"}],
            })
    return examples


def _read_sequences(path: Path) -> list[tuple[int, str]]:
    sequences: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        sequence = line.strip()
        if sequence and not sequence.startswith(">"):
            sequences.append((lineno, sequence))
    return sequences


def _load_or_seed_run_config(out_path: Path, hooks_yaml: Path) -> dict:
    if out_path.exists():
        existing = json.loads(out_path.read_text())
        if isinstance(existing, dict) and "run_config" in existing:
            return existing["run_config"]
    return {"activation_collection": yaml.safe_load(hooks_yaml.read_text())}


if __name__ == "__main__":
    main()
