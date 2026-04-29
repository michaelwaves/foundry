"""Convert a FASTA file into a SourceRow CSV.

This is the standard "first hop" after any download script: the downloader
produces FASTA, and this CLI materialises a sources.csv conforming to the
unified schema. Filters out non-canonical residues and optionally caps length.

Usage:
  python -m datasets.fasta_to_sources \\
      --fasta datasets/vfdb/VFDB_setA_pro.fas \\
      --label 1 --name-prefix vf \\
      --out datasets/vfdb/sources.csv \\
      --min-length 50 --max-length 300
"""
from __future__ import annotations

from pathlib import Path

import click

from .sources import SourceRow, write_sources


@click.command()
@click.option("--fasta", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--label", type=int, required=True, help="0=benign, 1=hazard")
@click.option("--name-prefix", type=str, required=True, help="prefix prepended to each FASTA accession")
@click.option("--min-length", type=int, default=1, show_default=True)
@click.option("--max-length", type=int, default=10_000, show_default=True)
def main(
    fasta: Path,
    out: Path,
    label: int,
    name_prefix: str,
    min_length: int,
    max_length: int,
) -> None:
    rows: list[SourceRow] = []
    skipped = 0
    for accession, sequence in _read_fasta(fasta):
        if not (min_length <= len(sequence) <= max_length):
            skipped += 1
            continue
        if not set(sequence) <= _CANONICAL_AA:
            skipped += 1
            continue
        rows.append(SourceRow(
            name=f"{name_prefix}_{accession}",
            label=label,
            sequence=sequence,
            n_residues=len(sequence),
        ))
    write_sources(out, rows)
    click.echo(f"wrote {len(rows)} rows -> {out} (skipped {skipped})")


def _read_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    accession: str | None = None
    chunks: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            if accession is not None:
                records.append((accession, "".join(chunks).replace("*", "")))
            accession = line[1:].split()[0].split("(")[0]
            chunks = []
        elif accession is not None:
            chunks.append(line.strip())
    if accession is not None:
        records.append((accession, "".join(chunks).replace("*", "")))
    return records


_CANONICAL_AA = set("ACDEFGHIKLMNPQRSTVWY")


if __name__ == "__main__":
    main()
