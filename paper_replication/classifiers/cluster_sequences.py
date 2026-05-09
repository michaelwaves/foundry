#!/usr/bin/env python3
"""Cluster the sequences behind a labels.csv with mmseqs2 → clusters.csv.

Reads the saffron-collect train_inputs.json to recover one sequence per
example (RF3: from `examples[].components[].seq`; RFD3: from chain A of the
referenced PDB), aligns them by source identifier with the labels.csv
`source_id` column, runs `mmseqs easy-cluster`, and writes a
`design_id,cluster_id` CSV for `split_labels.py --clusters`.

mmseqs path defaults to `~/tools/mmseqs/bin/mmseqs` (--mmseqs to override).

Usage:
  python cluster_sequences.py \\
      --labels rfd3_safeprotein/labels.csv \\
      --inputs ../sae_data_rfd3_partial/train_inputs.json \\
      --out rfd3_safeprotein/clusters.csv \\
      --min-seq-id 0.3 --coverage 0.8
"""
import argparse
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd


def main() -> None:
    args = _parse_args()
    sequences = _load_sequences(Path(args.inputs))
    labels = pd.read_csv(args.labels)
    used = {row["source_id"]: row["design_id"] for _, row in labels.iterrows()}
    fasta_records = [(src, sequences[src]) for src in used if src in sequences]
    missing = sorted(set(used) - {src for src, _ in fasta_records})
    if missing:
        print(f"warn: {len(missing)} source_ids missing sequence (skipped): {missing[:5]}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = Path(tmpdir) / "input.fasta"
        _write_fasta(fasta_path, fasta_records)
        cluster_tsv = _run_mmseqs(args.mmseqs, fasta_path, Path(tmpdir),
                                  args.min_seq_id, args.coverage)
        rep_by_member = _parse_cluster_tsv(cluster_tsv)

    _write_clusters_csv(Path(args.out), labels, rep_by_member)


def _load_sequences(inputs_json: Path) -> dict[str, str]:
    payload = json.loads(inputs_json.read_text())
    if isinstance(payload.get("examples"), list):
        return _rf3_sequences(payload["examples"])
    return _rfd3_sequences(payload, inputs_json.parent)


def _rf3_sequences(examples: list[dict]) -> dict[str, str]:
    return {ex["name"]: ex["components"][0]["seq"] for ex in examples}


def _rfd3_sequences(payload: dict, inputs_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, spec in payload.items():
        if not isinstance(spec, dict) or "input" not in spec:
            continue
        pdb_path = Path(spec["input"])
        if not pdb_path.is_absolute():
            pdb_path = inputs_dir / pdb_path
        sequence = _extract_chain_sequence(pdb_path)
        if sequence:
            out[name] = sequence
    return out


def _extract_chain_sequence(pdb_path: Path) -> str:
    seen: set[tuple[str, str]] = set()
    chain_id: str | None = None
    residues: list[str] = []
    with pdb_path.open() as fh:
        for line in fh:
            if not line.startswith("ATOM") or line[12:16].strip() != "CA":
                continue
            res_name = line[17:20].strip()
            one_letter = _THREE_TO_ONE.get(res_name)
            if one_letter is None:
                continue
            chain = line[21]
            if chain_id is None:
                chain_id = chain
            if chain != chain_id:
                continue
            key = (chain, line[22:27].strip())
            if key in seen:
                continue
            seen.add(key)
            residues.append(one_letter)
    return "".join(residues)


def _write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    with path.open("w") as f:
        for name, seq in records:
            f.write(f">{name}\n{seq}\n")


def _run_mmseqs(mmseqs_path: str, fasta: Path, workdir: Path,
                min_seq_id: float, coverage: float) -> Path:
    binary = Path(mmseqs_path).expanduser()
    if not binary.exists():
        raise SystemExit(f"mmseqs not found at {binary} (use --mmseqs)")
    out_prefix = workdir / "clusters"
    tmp_dir = workdir / "mmseqs_tmp"
    cmd = [str(binary), "easy-cluster", str(fasta), str(out_prefix), str(tmp_dir),
           "--min-seq-id", str(min_seq_id), "-c", str(coverage), "--cov-mode", "0"]
    print(f"running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return out_prefix.with_suffix("").parent / f"{out_prefix.name}_cluster.tsv"


def _parse_cluster_tsv(path: Path) -> dict[str, str]:
    rep_by_member: dict[str, str] = {}
    with path.open() as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 2:
                rep_by_member[row[1]] = row[0]
    return rep_by_member


def _write_clusters_csv(out: Path, labels: pd.DataFrame, rep_by_member: dict[str, str]) -> None:
    rows = []
    for _, row in labels.iterrows():
        cluster_id = rep_by_member.get(row["source_id"], row["source_id"])
        rows.append({"design_id": row["design_id"], "cluster_id": cluster_id})
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    n_clusters = len({r["cluster_id"] for r in rows})
    print(f"{len(rows)} designs -> {n_clusters} clusters -> {out}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--inputs", required=True,
                        help="train_inputs.json from saffron collect")
    parser.add_argument("--out", required=True)
    parser.add_argument("--mmseqs", default="~/tools/mmseqs/bin/mmseqs")
    parser.add_argument("--min-seq-id", type=float, default=0.3)
    parser.add_argument("--coverage", type=float, default=0.8)
    return parser.parse_args()


_THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


if __name__ == "__main__":
    main()
