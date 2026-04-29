"""PDB / mmCIF parsing helpers shared across the dataset utilities."""
from __future__ import annotations

import gzip
from pathlib import Path


def extract_chain_sequence(pdb_path: Path) -> str:
    """Return the first chain's amino-acid sequence as a one-letter string."""
    seen: set[tuple[str, str]] = set()
    chain_id: str | None = None
    residues: list[str] = []
    with pdb_path.open() as handle:
        for line in handle:
            if not line.startswith("ATOM") or line[12:16].strip() != "CA":
                continue
            one_letter = _THREE_TO_ONE.get(line[17:20].strip())
            if one_letter is None:
                continue
            chain = line[21]
            chain_id = chain_id or chain
            if chain != chain_id:
                continue
            key = (chain, line[22:27].strip())
            if key in seen:
                continue
            seen.add(key)
            residues.append(one_letter)
    return "".join(residues)


def first_missing_ca(pdb_path: Path) -> str | None:
    """Describe the first standard-AA residue without a CA atom (RFD3 chokes on these)."""
    atoms_by_residue: dict[tuple[str, str, str], set[str]] = {}
    order: list[tuple[str, str, str]] = []
    with pdb_path.open() as handle:
        for line in handle:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            res_name = line[17:20].strip()
            if res_name not in _STANDARD_AA:
                continue
            key = (line[21], line[22:27].strip(), res_name)
            if key not in atoms_by_residue:
                atoms_by_residue[key] = set()
                order.append(key)
            atoms_by_residue[key].add(line[12:16].strip())
    for key in order:
        if "CA" not in atoms_by_residue[key]:
            chain, res_seq, res_name = key
            return f"{res_name} {chain}{res_seq} missing CA"
    return None


def count_residues(structure_path: Path) -> tuple[int | None, int | None]:
    """Return (n_residues, min_residue_index) for a PDB or mmCIF file."""
    if not structure_path.exists():
        return None, None
    opener = gzip.open if structure_path.name.endswith(".gz") else open
    is_cif = ".cif" in structure_path.name
    col_chain = 6 if is_cif else 4
    col_resi = 8 if is_cif else 5
    residues: set[tuple[str, str]] = set()
    min_idx: int | None = None
    with opener(structure_path, "rt") as handle:
        for line in handle:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            cols = line.split()
            if len(cols) <= col_resi:
                continue
            chain, resi_str = cols[col_chain], cols[col_resi]
            residues.add((chain, resi_str))
            try:
                idx = int(resi_str)
            except ValueError:
                continue
            min_idx = idx if min_idx is None else min(min_idx, idx)
    return len(residues), min_idx


_THREE_TO_ONE: dict[str, str] = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}
_STANDARD_AA: frozenset[str] = frozenset(_THREE_TO_ONE)
