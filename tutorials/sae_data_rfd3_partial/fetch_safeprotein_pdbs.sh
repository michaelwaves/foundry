#!/usr/bin/env bash
# Fetch PDB files referenced in SafeProtein_Bench.json from RCSB and emit a
# sources.csv that build_inputs.py consumes.
#
# Behavior:
#   - For each accession in SafeProtein_Bench.json, pick the first PDB ID listed
#     in its 'PDB' dict (deterministic ordering).
#   - Download the .pdb file from RCSB (~50–500 KB each; 429 entries → ~50 MB).
#   - Emit sources.csv with columns: name, label, structure_path
#     (label=1 for hazards; benigns must be appended separately).
#
# Usage:
#   ./fetch_safeprotein_pdbs.sh                       # default dest: ./pdbs/
#   ./fetch_safeprotein_pdbs.sh /custom/dest

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SAFE_JSON="$HERE/../../detectors/datasets/safeprotein/SafeProtein_Bench.json"
DEST="${1:-$HERE/pdbs}"
SOURCES_CSV="$HERE/sources.csv"

if [[ ! -s "$SAFE_JSON" ]]; then
    echo "missing $SAFE_JSON — run detectors/datasets/download_safeprotein.sh first" >&2
    exit 1
fi

mkdir -p "$DEST"
echo "name,label,structure_path" > "$SOURCES_CSV"

python3 - "$SAFE_JSON" "$DEST" "$SOURCES_CSV" <<'PY'
import json, os, sys, urllib.error, urllib.request
from pathlib import Path


def _fetch_structure(pdb_id: str, dest: Path) -> Path | None:
    pid = pdb_id.lower()
    for filename in (f"{pid}.pdb", f"{pid}.cif.gz"):
        target = dest / filename
        if target.exists() and target.stat().st_size > 0:
            return target
        try:
            urllib.request.urlretrieve(f"https://files.rcsb.org/download/{filename}", target)
            return target
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            try: target.unlink()
            except FileNotFoundError: pass
    return None


src, dest_dir, csv_path = sys.argv[1:]
dest = Path(dest_dir)

with open(src) as f:
    data = json.load(f)

n_ok, n_skip = 0, 0
with open(csv_path, "a") as csv:
    for accession, record in data.items():
        pdb_dict = record.get("PDB") or {}
        if not pdb_dict:
            n_skip += 1
            continue
        pdb_id = sorted(pdb_dict.keys())[0].lower()
        target = _fetch_structure(pdb_id, dest)
        if target is None:
            print(f"  fail {accession} ({pdb_id}): no .pdb or .cif.gz at RCSB")
            n_skip += 1
            continue
        csv.write(f"hazard_{accession},1,{target.resolve()}\n")
        n_ok += 1
        if n_ok % 50 == 0:
            print(f"  {n_ok} fetched...")

print(f"done: {n_ok} fetched, {n_skip} skipped (no PDB or fetch error)")
PY

echo "wrote sources.csv -> $SOURCES_CSV"
