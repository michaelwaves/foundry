#!/usr/bin/env python3
"""Convert ToxinPred line-format CSVs into RF3 inference JSON.

Each peptide becomes one example. The example name matches the source_id format
emitted by `detect labels` for line-format CSVs (`{stem}_{lineno}`), so labels
align cleanly: design_id == example_id == source_id.

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


def main() -> None:
    args = _parse_args()
    rng = random.Random(args.seed)

    examples = []
    for path in args.positive:
        examples.extend(_make_examples(Path(path), rng, args.subsample))
    for path in args.negative:
        examples.extend(_make_examples(Path(path), rng, args.subsample))

    Path(args.out).write_text(json.dumps(examples, indent=2))
    print(f"wrote {len(examples)} examples -> {args.out}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive", action="append", default=[])
    parser.add_argument("--negative", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--subsample", type=int, default=None,
                        help="if set, randomly take this many sequences from each file")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--chain-id", default="A")
    return parser.parse_args()


def _make_examples(path: Path, rng: random.Random, subsample: int | None) -> list[dict]:
    sequences = _read_sequences(path)
    if subsample is not None and subsample < len(sequences):
        sequences = rng.sample(sequences, subsample)
    return [
        {
            "name": f"{path.stem}_{lineno}",
            "components": [{"seq": seq, "chain_id": "A"}],
        }
        for lineno, seq in sequences
    ]


def _read_sequences(path: Path) -> list[tuple[int, str]]:
    sequences: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        sequence = line.strip()
        if sequence and not sequence.startswith(">"):
            sequences.append((lineno, sequence))
    return sequences


if __name__ == "__main__":
    main()
