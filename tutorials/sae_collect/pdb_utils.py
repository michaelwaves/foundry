"""PDB parsing helpers used by the activation-collection input builders."""
from __future__ import annotations

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
    """Return a description of the first standard-AA residue missing a CA atom."""
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


_THREE_TO_ONE: dict[str, str] = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}
_STANDARD_AA: frozenset[str] = frozenset(_THREE_TO_ONE)
