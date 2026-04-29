"""Pair rows in a sources.csv with PDB / CIF files in a directory.

For each row, recursively searches `--pdb-dir` for the first file matching one
of `<name>.pdb`, `<name>.cif`, `<name>.cif.gz`, or `<name>_model.cif` and
populates `structure_path`. Rows without a match pass through unchanged.

Pairs cleanly with `rf3 fold` (the project's batch folder), which writes
predictions to `<out_dir>/<sample_idx>/<example_id>/<example_id>_model.cif`.

Usage:
  rf3 fold inputs=rf3_inputs.json out_dir=pdbs/ skip_existing=True
  python -m datasets.attach_pdbs \\
      --sources sources.csv --pdb-dir pdbs/ --out sources_with_pdbs.csv
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import click

from .sources import read_sources, write_sources

_SUFFIXES = ("_model.cif", ".cif.gz", ".pdb", ".cif")


@click.command()
@click.option("--sources", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--pdb-dir", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
def main(sources: Path, out: Path, pdb_dir: Path) -> None:
    name_to_path = _index_pdb_dir(pdb_dir)
    rows = read_sources(sources)
    n_attached = n_missing = 0
    enriched = []
    for row in rows:
        path = name_to_path.get(row.name)
        if path is None:
            n_missing += 1
            enriched.append(row)
            continue
        enriched.append(replace(row, structure_path=path.resolve()))
        n_attached += 1
    write_sources(out, enriched)
    click.echo(f"attached={n_attached} no-match={n_missing} -> {out}")


def _index_pdb_dir(pdb_dir: Path) -> dict[str, Path]:
    """Return {name: path} for every file in pdb_dir whose stem matches a known suffix."""
    index: dict[str, Path] = {}
    for path in pdb_dir.rglob("*"):
        if not path.is_file():
            continue
        name = _name_from_filename(path.name)
        if name is not None and name not in index:
            index[name] = path
    return index


def _name_from_filename(filename: str) -> str | None:
    for suffix in _SUFFIXES:
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return None


if __name__ == "__main__":
    main()
