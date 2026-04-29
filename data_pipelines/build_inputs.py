"""Build a saffron-collect inputs JSON from a sources.csv or HF dataset.

Source providers (mutually exclusive):
- `--sources path.csv`: read a local SourceRow CSV.
- `--hf-dataset NAME`: pull from a HuggingFace dataset; if rows carry
  `pdb_bytes`, materialise them to `--pdb-cache-dir` so RFD3 can find PDB paths.

Dispatches on `--model`:
- `rfd3` requires `structure_path`; emits dict-of-name with `input` + `partial_t`.
- `rf3` accepts `sequence` directly or extracts it from `structure_path` (chain A).

Run `saffron collect` separately afterwards:

  python -m data_pipelines.build_inputs \\
      --hf-dataset baker-lab/foundry-safeprotein \\
      --out train_inputs.json --model rfd3 \\
      --hooks-yaml data_pipelines/hooks/rfd3_partial.yaml

  saffron collect model=rfd3 inputs=train_inputs.json out_dir=...
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import click
import yaml

from .pdb_utils import extract_chain_sequence, first_missing_ca
from .sources import SourceRow, read_sources

DEFAULT_PDB_CACHE = Path("~/.cache/foundry/pdbs").expanduser()


@click.command()
@click.option("--sources", type=click.Path(exists=True, path_type=Path), default=None,
              help="local SourceRow CSV (mutually exclusive with --hf-dataset)")
@click.option("--hf-dataset", type=str, default=None,
              help="HuggingFace dataset NAME (e.g. baker-lab/foundry-safeprotein)")
@click.option("--hf-split", type=str, default="train", show_default=True)
@click.option("--pdb-cache-dir", type=click.Path(path_type=Path), default=DEFAULT_PDB_CACHE,
              show_default=True, help="where to write PDB bytes pulled from HF")
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--model", type=click.Choice(["rfd3", "rf3"]), required=True)
@click.option("--hooks-yaml", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--partial-t", type=float, default=5.0, show_default=True,
              help="rfd3 only: Å of noise for partial diffusion")
@click.option("--subsample", type=int, default=None,
              help="if set, randomly take this many rows")
@click.option("--seed", type=int, default=0)
def main(
    sources: Path | None, hf_dataset: str | None, hf_split: str,
    pdb_cache_dir: Path, out: Path, model: str, hooks_yaml: Path,
    partial_t: float, subsample: int | None, seed: int,
) -> None:
    if (sources is None) == (hf_dataset is None):
        raise click.UsageError("provide exactly one of --sources or --hf-dataset")
    rows = read_sources(sources) if sources else _load_from_hf(hf_dataset, hf_split, pdb_cache_dir)
    if subsample is not None and subsample < len(rows):
        rows = random.Random(seed).sample(rows, subsample)
    run_config = _load_or_seed_run_config(out, hooks_yaml)
    payload, kept, skipped = _build_payload(rows, model, run_config, partial_t)

    out.write_text(json.dumps(payload, indent=2))
    for line in skipped:
        click.echo(f"skip {line}")
    click.echo(f"wrote {kept} examples + run_config -> {out} (skipped {len(skipped)})")


def _load_from_hf(name: str, split: str, cache_dir: Path) -> list[SourceRow]:
    from datasets import load_dataset    # lazy: HF dep is optional

    dataset = load_dataset(name, split=split)
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows: list[SourceRow] = []
    for record in dataset:
        structure_path = _materialise_pdb(record, cache_dir)
        rows.append(SourceRow(
            name=record["name"], label=record["label"],
            sequence=record.get("sequence"),
            structure_path=structure_path,
            n_residues=record.get("n_residues"),
            min_residue=record.get("min_residue"),
        ))
    return rows


def _materialise_pdb(record: dict, cache_dir: Path) -> Path | None:
    pdb_bytes = record.get("pdb_bytes")
    if not pdb_bytes:
        return None
    filename = record.get("pdb_filename") or f"{record['name']}.pdb"
    path = cache_dir / filename
    if not path.exists():
        path.write_bytes(pdb_bytes)
    return path.resolve()


def _build_payload(
    rows: list[SourceRow], model: str, run_config: dict, partial_t: float,
) -> tuple[dict, int, list[str]]:
    if model == "rfd3":
        body, skipped = _build_rfd3_payload(rows, partial_t)
        return {"run_config": run_config, **body}, len(body), skipped
    examples, skipped = _build_rf3_payload(rows)
    return {"run_config": run_config, "examples": examples}, len(examples), skipped


def _build_rfd3_payload(rows: list[SourceRow], partial_t: float) -> tuple[dict, list[str]]:
    payload: dict = {}
    skipped: list[str] = []
    for row in rows:
        if row.structure_path is None:
            skipped.append(f"{row.name}: missing structure_path")
            continue
        path = row.structure_path.resolve()
        reason = first_missing_ca(path)
        if reason is not None:
            skipped.append(f"{row.name} ({path.name}): {reason}")
            continue
        payload[row.name] = {"input": str(path), "partial_t": partial_t}
    return payload, skipped


def _build_rf3_payload(rows: list[SourceRow]) -> tuple[list[dict], list[str]]:
    examples: list[dict] = []
    skipped: list[str] = []
    for row in rows:
        sequence = row.sequence
        if not sequence and row.structure_path is not None:
            sequence = extract_chain_sequence(row.structure_path.resolve())
        if not sequence:
            skipped.append(f"{row.name}: no sequence available")
            continue
        examples.append({"name": row.name, "components": [{"seq": sequence, "chain_id": "A"}]})
    return examples, skipped


def _load_or_seed_run_config(out_json: Path, hooks_yaml: Path) -> dict:
    if out_json.exists():
        existing = json.loads(out_json.read_text())
        if isinstance(existing, dict) and "run_config" in existing:
            return existing["run_config"]
    return {"activation_collection": yaml.safe_load(hooks_yaml.read_text())}


if __name__ == "__main__":
    main()
