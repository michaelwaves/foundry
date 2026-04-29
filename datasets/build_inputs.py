"""Build a saffron-collect inputs JSON from a unified sources.csv.

Dispatches on `--model`:
- `rfd3` requires `structure_path`; emits dict-of-name with `input` + `partial_t`.
- `rf3` accepts `sequence` directly or extracts it from `structure_path` (chain A).

Decoupled from `saffron collect` — run that yourself afterwards:

  python -m datasets.build_inputs \\
      --sources datasets/safeprotein/sources.csv \\
      --out tutorials/sae_data_rfd3_partial/train_inputs.json \\
      --model rfd3 \\
      --hooks-yaml datasets/hooks/rfd3_partial.yaml \\
      --partial-t 5.0

  saffron collect \\
      model=rfd3 \\
      inputs=tutorials/sae_data_rfd3_partial/train_inputs.json \\
      out_dir=tutorials/sae_data_rfd3_partial/train_activations
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import click
import yaml

from .pdb_utils import extract_chain_sequence, first_missing_ca
from .sources import SourceRow, read_sources


@click.command()
@click.option("--sources", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--model", type=click.Choice(["rfd3", "rf3"]), required=True)
@click.option("--hooks-yaml", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--partial-t", type=float, default=5.0, show_default=True,
              help="rfd3 only: Å of noise for partial diffusion")
@click.option("--subsample", type=int, default=None,
              help="if set, randomly take this many rows")
@click.option("--seed", type=int, default=0)
def main(
    sources: Path, out: Path, model: str, hooks_yaml: Path,
    partial_t: float, subsample: int | None, seed: int,
) -> None:
    rows = read_sources(sources)
    if subsample is not None and subsample < len(rows):
        rows = random.Random(seed).sample(rows, subsample)
    run_config = _load_or_seed_run_config(out, hooks_yaml)
    payload, kept, skipped = _build_payload(rows, model, run_config, partial_t)

    out.write_text(json.dumps(payload, indent=2))
    for line in skipped:
        click.echo(f"skip {line}")
    click.echo(f"wrote {kept} examples + run_config -> {out} (skipped {len(skipped)})")


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
