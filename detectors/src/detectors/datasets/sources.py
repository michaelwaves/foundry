"""Unified source-row schema for activation-collection pipelines.

Every dataset (SafeProtein, VFDB, ToxinPred, UniProt benigns, ...) emits one
sources CSV with this schema, and every downstream consumer (build_inputs,
balance, fold, ...) reads/writes it through here.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class SourceRow:
    name: str
    label: int
    sequence: str | None = None
    structure_path: Path | None = None
    n_residues: int | None = None
    min_residue: int | None = None


def read_sources(path: Path) -> list[SourceRow]:
    with path.open() as handle:
        return [_row_from_dict(row) for row in csv.DictReader(handle)]


def write_sources(path: Path, rows: list[SourceRow]) -> None:
    field_names = [f.name for f in fields(SourceRow)]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_names)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if v is None else v) for k, v in asdict(row).items()})


def filter_by_length(
    rows: list[SourceRow],
    max_residues: int,
    min_residues: int = 1,
) -> list[SourceRow]:
    return [
        row for row in rows
        if row.n_residues is not None and min_residues <= row.n_residues <= max_residues
    ]


def _row_from_dict(row: dict[str, str]) -> SourceRow:
    structure_path = row.get("structure_path") or None
    return SourceRow(
        name=row["name"],
        label=int(row["label"]),
        sequence=row.get("sequence") or None,
        structure_path=Path(structure_path) if structure_path else None,
        n_residues=_optional_int(row.get("n_residues")),
        min_residue=_optional_int(row.get("min_residue")),
    )


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None
