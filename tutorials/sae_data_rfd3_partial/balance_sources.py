#!/usr/bin/env python3
"""Filter + length-stratified subsample a sources.csv for partial-diffusion runs.

Reads a sources CSV (columns: name, label, structure_path; optional n_residues)
and writes a class-balanced subsample where for each length bin we take
min(#hazard, #benign), discarding everything above max_residues.

If the input lacks `n_residues`, residue counts are computed on the fly by parsing
the PDB/CIF files and a sidecar `<input>_counts.csv` is written for reuse.

Usage:
  python balance_sources.py --input sources.csv --output sources.csv
  python balance_sources.py --input sources.csv --output balanced.csv --max-residues 250
"""
import argparse
import csv
import gzip
import random
from collections import defaultdict
from pathlib import Path


def main() -> None:
    args = _parse_args()
    rows = _load_with_counts(Path(args.input))
    kept = _stratified_balance(rows, args.max_residues, args.bin_size, args.seed)
    Path(args.output).write_text("name,label,structure_path\n" + "\n".join(
        f"{r['name']},{r['label']},{r['structure_path']}" for r in kept
    ))
    n_haz = sum(1 for r in kept if r["label"] == "1")
    print(f"wrote {len(kept)} rows -> {args.output}")
    print(f"  hazards: {n_haz}  benigns: {len(kept) - n_haz}  (balanced per {args.bin_size}-residue bin)")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with name,label,structure_path[,n_residues]")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-residues", type=int, default=300)
    parser.add_argument("--bin-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def _load_with_counts(input_path: Path) -> list[dict]:
    rows = list(csv.DictReader(input_path.open()))
    if rows and "n_residues" in rows[0]:
        return rows
    print(f"  no n_residues column — counting residues for {len(rows)} structures...")
    for i, row in enumerate(rows):
        if i % 100 == 0 and i > 0:
            print(f"    counted {i}/{len(rows)}")
        path_str = row.get("structure_path") or ""
        row["n_residues"] = str(_count_residues(Path(path_str))) if path_str else ""
    sidecar = input_path.with_name(input_path.stem + "_counts.csv")
    fields = list(rows[0].keys())
    with sidecar.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  cached counts -> {sidecar}")
    return rows


def _count_residues(path: Path) -> int:
    if not path.exists():
        return -1
    opener = gzip.open if path.suffix == ".gz" else open
    residues: set[tuple[str, str]] = set()
    try:
        with opener(path, "rt") as f:
            for line in f:
                if line.startswith("ATOM"):
                    cols = line.split()
                    if len(cols) > 8:
                        residues.add((cols[6], cols[8]))
    except Exception:
        return -1
    return len(residues)


def _stratified_balance(rows: list[dict], max_residues: int, bin_size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    buckets: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        try:
            n = int(row["n_residues"])
        except (ValueError, KeyError):
            continue
        if 0 <= n <= max_residues:
            buckets[(row["label"], (n // bin_size) * bin_size)].append(row)

    kept: list[dict] = []
    print(f"  {'bin':>10}  {'haz':>4}  {'ben':>4}  {'taken':>5}")
    for bucket in sorted({b for (_, b) in buckets}):
        haz = buckets.get(("1", bucket), [])
        ben = buckets.get(("0", bucket), [])
        n_take = min(len(haz), len(ben))
        if n_take > 0:
            kept.extend(rng.sample(haz, n_take) + rng.sample(ben, n_take))
        print(f"  {bucket:>4}-{bucket+bin_size-1:>4}  {len(haz):>4}  {len(ben):>4}  {n_take:>5}")

    rng.shuffle(kept)
    return kept


if __name__ == "__main__":
    main()
