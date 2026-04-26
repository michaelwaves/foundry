#!/usr/bin/env python3
"""Filter + length-stratified subsample a sources.csv for partial-diffusion runs.

Drops:
 - structures with > max_residues residues (GPU memory cap)
 - structures with non-positive residue indices (RFD3's contig parser rejects
   `A-1`, `A0`, etc. — common in PDBs that number from a tag/cleavage site)

Then takes min(#hazard, #benign) per length bin to remove length as a shortcut feature.

If the input lacks `n_residues` / `min_residue` columns, they are computed by parsing
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
    parser.add_argument("--input", required=True, help="CSV with name,label,structure_path[,n_residues,min_residue]")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-residues", type=int, default=300)
    parser.add_argument("--bin-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def _load_with_counts(input_path: Path) -> list[dict]:
    rows = list(csv.DictReader(input_path.open()))
    if not rows:
        return rows
    missing = {"n_residues", "min_residue"} - set(rows[0])
    if not missing:
        return rows
    print(f"  computing missing columns {sorted(missing)} for {len(rows)} structures...")
    for i, row in enumerate(rows):
        if i % 100 == 0 and i > 0:
            print(f"    {i}/{len(rows)}")
        n, m = _residue_stats(Path(row.get("structure_path") or ""))
        if "n_residues" in missing:
            row["n_residues"] = str(n) if n is not None else ""
        if "min_residue" in missing:
            row["min_residue"] = str(m) if m is not None else ""
    sidecar = input_path.with_name(input_path.stem + "_counts.csv")
    fields = list(rows[0].keys())
    with sidecar.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  cached -> {sidecar}")
    return rows


def _residue_stats(path: Path) -> tuple[int | None, int | None]:
    """Returns (n_residues, min_residue_index). Format-aware: PDB uses cols[4]/[5],
    mmCIF uses cols[6]/[8] in the atom_site loop."""
    if not path.exists():
        return None, None
    opener = gzip.open if path.name.endswith(".gz") else open
    is_cif = ".cif" in path.name
    col_chain = 6 if is_cif else 4
    col_resi = 8 if is_cif else 5
    residues: set[tuple[str, str]] = set()
    min_idx: int | None = None
    try:
        with opener(path, "rt") as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    cols = line.split()
                    if len(cols) <= col_resi:
                        continue
                    chain, resi_str = cols[col_chain], cols[col_resi]
                    residues.add((chain, resi_str))
                    try:
                        idx = int(resi_str)
                        min_idx = idx if min_idx is None else min(min_idx, idx)
                    except ValueError:
                        pass
    except Exception:
        return None, None
    return len(residues), min_idx


def _stratified_balance(rows: list[dict], max_residues: int, bin_size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    buckets: dict[tuple[str, int], list[dict]] = defaultdict(list)
    n_oversize = n_neg = 0
    for row in rows:
        try:
            n = int(row["n_residues"])
            m = int(row["min_residue"])
        except (ValueError, KeyError, TypeError):
            continue
        if n > max_residues:
            n_oversize += 1
            continue
        if m < 1:
            n_neg += 1
            continue
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
    print(f"  dropped: {n_oversize} oversize, {n_neg} with non-positive residue indices")

    rng.shuffle(kept)
    return kept


if __name__ == "__main__":
    main()
