"""Filter a combined sources.csv for RFD3-compatibility and class balance.

Operates on a *combined* sources.csv (hazards + benigns concatenated). Two filters:

1. Drops rows with non-positive `min_residue` — RFD3's contig parser rejects
   `A0`/`A-1` numbering common in PDBs that count from a tag/cleavage site.
2. Pairs `min(#hazard, #benign)` per `--bin-size` length bucket so length isn't
   a shortcut feature in downstream probes.

Assumes `n_residues` is already populated (set by `fasta_to_sources`).
`min_residue` is only populated when PDBs have been parsed; if absent, the
neg-index filter is skipped (a no-op for the RF3 path).

Usage:
  python -m datasets.filter_pdbs \\
      --sources datasets/safeprotein/sources_combined.csv \\
      --out datasets/safeprotein/sources_filtered.csv \\
      --bin-size 50
"""
from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

import click

from .sources import SourceRow, read_sources, write_sources


@click.command()
@click.option("--sources", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--bin-size", type=int, default=50, show_default=True)
@click.option("--seed", type=int, default=0)
def main(sources: Path, out: Path, bin_size: int, seed: int) -> None:
    rows = read_sources(sources)
    kept = _stratified_balance(rows, bin_size, seed)
    write_sources(out, kept)
    n_haz = sum(1 for row in kept if row.label == 1)
    click.echo(f"wrote {len(kept)} rows -> {out} (hazards={n_haz}, benigns={len(kept)-n_haz})")


def _stratified_balance(rows: list[SourceRow], bin_size: int, seed: int) -> list[SourceRow]:
    rng = random.Random(seed)
    buckets: dict[tuple[int, int], list[SourceRow]] = defaultdict(list)
    n_neg_index = n_unknown = 0
    for row in rows:
        if row.n_residues is None:
            n_unknown += 1
            continue
        if row.min_residue is not None and row.min_residue < 1:
            n_neg_index += 1
            continue
        buckets[(row.label, (row.n_residues // bin_size) * bin_size)].append(row)

    kept: list[SourceRow] = []
    for bucket in sorted({b for (_, b) in buckets}):
        haz = buckets.get((1, bucket), [])
        ben = buckets.get((0, bucket), [])
        n_take = min(len(haz), len(ben))
        if n_take > 0:
            kept.extend(rng.sample(haz, n_take) + rng.sample(ben, n_take))
        click.echo(f"  {bucket:>4}-{bucket+bin_size-1:>4}  haz={len(haz):>4}  ben={len(ben):>4}  taken={n_take:>4}")
    click.echo(f"  dropped: {n_neg_index} neg-indexed, {n_unknown} missing n_residues")

    rng.shuffle(kept)
    return kept


if __name__ == "__main__":
    main()
