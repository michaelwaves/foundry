"""Extract sequences from steered CIF outputs and write a combined FASTA.

Usage:
    python extract_sequences.py --sweep_dir outputs/steering/sweep --out_fasta outputs/steering/sweep/sequences.fasta
"""
import gzip
import re
from dataclasses import dataclass
from pathlib import Path

import click


_THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


@dataclass
class DesignRecord:
    design_id: str
    alpha: str
    sequence: str


@click.command()
@click.option("--sweep_dir", default="outputs/steering/sweep", type=click.Path())
@click.option("--out_fasta", default="outputs/steering/sweep/sequences.fasta", type=click.Path())
def main(sweep_dir: str, out_fasta: str) -> None:
    records = _collect_records(Path(sweep_dir))
    _write_fasta(records, Path(out_fasta))
    print(f"wrote {len(records)} sequences to {out_fasta}")


def _collect_records(sweep_dir: Path) -> list[DesignRecord]:
    records = []
    for condition_dir in sorted(p for p in sweep_dir.iterdir() if p.is_dir()):
        condition = condition_dir.name
        for cif_path in sorted(condition_dir.glob("*.cif.gz")):
            seq = _sequence_from_cif(cif_path)
            if seq:
                records.append(DesignRecord(
                    design_id=cif_path.stem,
                    alpha=condition,
                    sequence=seq,
                ))
    return records


def _sequence_from_cif(path: Path) -> str:
    opener = gzip.open if path.suffix == ".gz" else open
    residues: dict[int, str] = {}
    with opener(path, "rt") as f:
        in_atom_loop = False
        col_comp = col_seq = col_atom = None
        for line in f:
            line = line.rstrip()
            if line.startswith("_atom_site.label_comp_id"):
                in_atom_loop = True
            if not in_atom_loop:
                continue
            if line.startswith("_atom_site."):
                cols = _atom_site_columns(path)
                col_comp = cols.get("label_comp_id")
                col_seq = cols.get("label_seq_id")
                col_atom = cols.get("label_atom_id")
                break

    # Re-parse with known column indices
    col_comp, col_seq, col_atom = _atom_site_columns(path).values() if False else (
        *[None]*3,
    )
    cols = _atom_site_columns(path)
    col_comp = cols.get("label_comp_id")
    col_seq = cols.get("label_seq_id")
    col_atom = cols.get("label_atom_id")

    if col_comp is None or col_seq is None or col_atom is None:
        return ""

    with opener(path, "rt") as f:
        in_data = False
        for line in f:
            line = line.rstrip()
            if line.startswith("ATOM") or line.startswith("HETATM"):
                in_data = True
                parts = line.split()
                if len(parts) <= max(col_comp, col_seq, col_atom):
                    continue
                atom_name = parts[col_atom]
                if atom_name != "CA":
                    continue
                try:
                    seq_id = int(parts[col_seq])
                except ValueError:
                    continue
                comp = parts[col_comp]
                aa = _THREE_TO_ONE.get(comp)
                if aa:
                    residues[seq_id] = aa
            elif in_data and line.startswith("#"):
                break

    if not residues:
        return ""
    return "".join(residues[k] for k in sorted(residues))


def _atom_site_columns(path: Path) -> dict[str, int]:
    opener = gzip.open if path.suffix == ".gz" else open
    cols: dict[str, int] = {}
    idx = 0
    in_loop = False
    with opener(path, "rt") as f:
        for line in f:
            line = line.rstrip()
            if line == "loop_":
                in_loop = True
                idx = 0
                cols = {}
            elif in_loop and line.startswith("_atom_site."):
                key = line.split(".")[1]
                cols[key] = idx
                idx += 1
            elif in_loop and (line.startswith("ATOM") or line.startswith("HETATM")):
                break
    return cols


def _write_fasta(records: list[DesignRecord], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for r in records:
            f.write(f">{r.design_id}|{r.alpha}\n{r.sequence}\n")


if __name__ == "__main__":
    main()
