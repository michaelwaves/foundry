#!/usr/bin/env python3
"""Build labels.csv from an activations h5 by reading class from each design_id's prefix.

Works for any saffron-collected dataset where the prefix encodes the class:
  RFD3 SafeProtein/UniProt:  hazard_*  / benign_*  (inputs-stem = "train_inputs")
  RF3  ToxinPred3:           train_pos_* / train_neg_*   (inputs-stem = "")

Usage:
  python build_rfd3_labels.py \
      --activations <h5> \
      --hook <hook> \
      --positive-prefix <p> \
      --negative-prefix <n> \
      --inputs-stem <stem-or-empty> \
      --out <labels.csv>
"""
import argparse
import csv
from pathlib import Path

import h5py


def main() -> None:
    args = _parse_args()
    design_ids = _read_design_ids(Path(args.activations), args.hook)
    rows = [_label_row(d, args.positive_prefix, args.negative_prefix, args.inputs_stem) for d in design_ids]
    rows = [r for r in rows if r is not None]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.out).open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["design_id", "label", "source_id"])
        writer.writerows(rows)
    n_pos = sum(int(r[1]) for r in rows)
    print(f"wrote {len(rows)} labels ({n_pos} pos / {len(rows) - n_pos} neg) -> {args.out}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activations", required=True, help="h5 file from saffron collect")
    parser.add_argument("--hook", default="block6", help="any hook present in the h5")
    parser.add_argument("--out", required=True)
    parser.add_argument("--positive-prefix", default="hazard_")
    parser.add_argument("--negative-prefix", default="benign_")
    parser.add_argument("--inputs-stem", default="train_inputs",
                        help="leading inputs-JSON stem to strip before checking the class prefix; pass '' if absent")
    return parser.parse_args()


def _read_design_ids(activations_path: Path, hook: str) -> list[str]:
    with h5py.File(activations_path, "r") as f:
        if hook not in f:
            raise KeyError(f"hook '{hook}' not in {list(f.keys())}")
        return sorted(f[hook].keys())


def _label_row(design_id: str, positive: str, negative: str, inputs_stem: str) -> tuple[str, str, str] | None:
    source = _strip_inputs_prefix(design_id, inputs_stem)
    if source.startswith(positive):
        return design_id, "1", source
    if source.startswith(negative):
        return design_id, "0", source
    print(f"skip {design_id}: prefix doesn't match {positive!r} or {negative!r}")
    return None


def _strip_inputs_prefix(design_id: str, inputs_stem: str) -> str:
    if inputs_stem and design_id.startswith(f"{inputs_stem}_"):
        body = design_id[len(inputs_stem) + 1:]
        if "_" in body and body.rsplit("_", 1)[1].isdigit():
            body = body.rsplit("_", 1)[0]
        return body
    return design_id


if __name__ == "__main__":
    main()
