"""Download PDBs from RCSB for rows in a sources.csv, populating `structure_path`.

Pick one mapping provider:
- `--pdb-map`: JSON `{row_name: pdb_id, ...}`
- `--safeprotein-json`: SafeProtein_Bench.json — keys are bare UniProt accessions,
  values are dicts with a `PDB` field whose keys are PDB IDs. The first sorted
  PDB ID per accession is used.

Use `--strip-prefix` when sources.csv names carry a class prefix (e.g. names
look like `hazard_P12345` but the provider is keyed by `P12345`).

Usage:
  python -m detectors.datasets.fetch_pdbs \\
      --sources detectors/datasets/safeprotein/sources.csv \\
      --safeprotein-json detectors/datasets/safeprotein/SafeProtein_Bench.json \\
      --strip-prefix hazard_ \\
      --pdb-dir detectors/datasets/safeprotein/pdbs \\
      --out detectors/datasets/safeprotein/sources_with_pdbs.csv
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

import click

from .sources import SourceRow, read_sources, write_sources


@click.command()
@click.option("--sources", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--pdb-dir", type=click.Path(path_type=Path), required=True)
@click.option("--pdb-map", type=click.Path(exists=True, path_type=Path), default=None,
              help="JSON mapping row_name -> pdb_id")
@click.option("--safeprotein-json", type=click.Path(exists=True, path_type=Path), default=None,
              help="SafeProtein_Bench.json (extracts PDB refs)")
@click.option("--strip-prefix", type=str, default="",
              help="strip this prefix from row.name before mapping lookup")
def main(
    sources: Path, out: Path, pdb_dir: Path,
    pdb_map: Path | None, safeprotein_json: Path | None, strip_prefix: str,
) -> None:
    if (pdb_map is None) == (safeprotein_json is None):
        raise click.UsageError("provide exactly one of --pdb-map or --safeprotein-json")
    mapping = _load_mapping(pdb_map, safeprotein_json)
    pdb_dir.mkdir(parents=True, exist_ok=True)

    enriched: list[SourceRow] = []
    n_fetched = n_missing = n_failed = 0
    for row in read_sources(sources):
        accession = row.name.removeprefix(strip_prefix)
        pdb_id = mapping.get(accession)
        if pdb_id is None:
            n_missing += 1
            enriched.append(row)
            continue
        path = fetch_one_pdb(pdb_id, pdb_dir)
        if path is None:
            n_failed += 1
            enriched.append(row)
            continue
        enriched.append(replace(row, structure_path=path.resolve()))
        n_fetched += 1
    write_sources(out, enriched)
    click.echo(f"fetched={n_fetched} no-mapping={n_missing} download-failed={n_failed} -> {out}")


def fetch_one_pdb(pdb_id: str, dest_dir: Path) -> Path | None:
    pid = pdb_id.lower()
    for filename in (f"{pid}.pdb", f"{pid}.cif.gz"):
        target = dest_dir / filename
        if target.exists() and target.stat().st_size > 0:
            return target
        try:
            urllib.request.urlretrieve(f"https://files.rcsb.org/download/{filename}", target)
            return target
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            target.unlink(missing_ok=True)
    return None


def _load_mapping(pdb_map: Path | None, safeprotein_json: Path | None) -> dict[str, str]:
    if pdb_map is not None:
        return json.loads(pdb_map.read_text())
    data = json.loads(safeprotein_json.read_text())  # type: ignore[union-attr]
    return {
        accession: sorted(record["PDB"].keys())[0].lower()
        for accession, record in data.items()
        if record.get("PDB")
    }


if __name__ == "__main__":
    main()
