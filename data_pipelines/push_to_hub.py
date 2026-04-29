"""Push a sources.csv to a HuggingFace Dataset repo.

Each SourceRow becomes one record. With `--include-pdb-bytes`, rows that have
a `structure_path` get their file contents bundled as `pdb_bytes` plus a
`pdb_filename`, so the dataset is fully self-contained (downstream consumers
materialise the PDBs to a cache dir at load time).

Usage:
  python -m data_pipelines.push_to_hub \\
      --sources data_pipelines/safeprotein/sources_with_pdbs.csv \\
      --hf-repo baker-lab/foundry-safeprotein \\
      --include-pdb-bytes
"""
from __future__ import annotations

from pathlib import Path

import click

from .sources import SourceRow, read_sources


@click.command()
@click.option("--sources", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--hf-repo", type=str, required=True, help="user_or_org/dataset_name")
@click.option("--include-pdb-bytes", is_flag=True, default=False,
              help="bundle PDB file bytes from structure_path into the dataset")
@click.option("--private", is_flag=True, default=False,
              help="create / push to a private repo")
@click.option("--split", type=str, default="train", show_default=True)
def main(
    sources: Path, hf_repo: str, include_pdb_bytes: bool, private: bool, split: str,
) -> None:
    from datasets import Dataset   # lazy: HF dep is optional

    rows = read_sources(sources)
    records = [_to_record(row, include_pdb_bytes) for row in rows]
    dataset = Dataset.from_list(records)
    dataset.push_to_hub(hf_repo, split=split, private=private)
    click.echo(f"pushed {len(records)} rows -> {hf_repo} ({split})")


def _to_record(row: SourceRow, include_pdb_bytes: bool) -> dict:
    record = {
        "name": row.name,
        "label": row.label,
        "sequence": row.sequence,
        "n_residues": row.n_residues,
        "min_residue": row.min_residue,
    }
    if include_pdb_bytes and row.structure_path is not None:
        record["pdb_bytes"] = row.structure_path.read_bytes()
        record["pdb_filename"] = row.structure_path.name
    return record


if __name__ == "__main__":
    main()
