"""Model-specific payload builders for the unified saffron-collect inputs JSON.

`build_rfd3_payload` emits the dict-of-name shape RFD3 expects (each value has
`input` + `partial_t`). `build_rf3_payload` emits the list-of-examples shape
RF3 expects (each entry carries a sequence and chain id).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from detectors.datasets.sources import SourceRow

from .pdb_utils import extract_chain_sequence, first_missing_ca


def build_rfd3_payload(rows: list[SourceRow], partial_t: float) -> tuple[dict, list[str]]:
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


def build_rf3_payload(rows: list[SourceRow]) -> tuple[list[dict], list[str]]:
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


def load_or_seed_run_config(out_json: Path, hooks_yaml: Path) -> dict:
    if out_json.exists():
        existing = json.loads(out_json.read_text())
        if isinstance(existing, dict) and "run_config" in existing:
            return existing["run_config"]
    return {"activation_collection": yaml.safe_load(hooks_yaml.read_text())}
