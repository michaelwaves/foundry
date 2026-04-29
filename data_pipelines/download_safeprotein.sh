#!/usr/bin/env bash
# Download SafeProtein hazard set (~6.8 MB JSON) and extract a FASTA + accession list.
# Source: https://github.com/jigang-fan/SafeProtein
# Each record: UniProt accession -> {Length, Sequence, PDB, conservation_scores}.
# This is the positive (hazard) set used by SafeBench-Seq.
#
# Usage:
#   ./download_safeprotein.sh              # default: ./safeprotein/
#   ./download_safeprotein.sh /dest

set -euo pipefail

DEST="${1:-$(dirname "$0")/safeprotein}"
URL="https://raw.githubusercontent.com/jigang-fan/SafeProtein/main/SafeProtein_Bench.json"

mkdir -p "$DEST"
json_target="$DEST/SafeProtein_Bench.json"
fasta_target="$DEST/safeprotein.fasta"
accessions_target="$DEST/accessions.txt"

if [[ ! -s "$json_target" ]]; then
    echo "fetch  $URL -> $json_target"
    curl -fsSL "$URL" -o "$json_target"
else
    echo "skip   $json_target (already exists)"
fi

python3 - "$json_target" "$fasta_target" "$accessions_target" <<'PY'
import json, sys
src, fasta_path, acc_path = sys.argv[1:]
with open(src) as f:
    data = json.load(f)
with open(fasta_path, "w") as fasta, open(acc_path, "w") as acc:
    for accession, record in data.items():
        fasta.write(f">{accession}\n{record['Sequence']}\n")
        acc.write(f"{accession}\n")
print(f"wrote {len(data)} records -> {fasta_path}")
PY
