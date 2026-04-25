#!/usr/bin/env bash
# Download VFDB (Virulence Factor Database) protein FASTA files.
# Source: https://www.mgc.ac.cn/VFs/download.htm
#
# Set A (core, experimentally verified VFs): ~1.3 MB gz
# Set B (full, includes predicted VFs):      ~5.6 MB gz
#
# Usage:
#   ./download_vfdb.sh              # default: ./vfdb/, set A only
#   ./download_vfdb.sh full         # set B (full)
#   ./download_vfdb.sh full /dest

set -euo pipefail

MODE="${1:-core}"
DEST="${2:-$(dirname "$0")/vfdb}"
BASE="https://www.mgc.ac.cn/VFs/Down"

declare -A FILES
FILES[core]="VFDB_setA_pro.fas.gz"
FILES[full]="VFDB_setB_pro.fas.gz"

if [[ -z "${FILES[$MODE]:-}" ]]; then
    echo "error: mode must be 'core' or 'full', got '$MODE'" >&2
    exit 1
fi

mkdir -p "$DEST"
remote="${FILES[$MODE]}"
gz_target="$DEST/$remote"
fasta_target="${gz_target%.gz}"

if [[ -s "$fasta_target" ]]; then
    echo "skip   $fasta_target (already exists)"
else
    echo "fetch  $BASE/$remote -> $gz_target"
    curl -fsSL "$BASE/$remote" -o "$gz_target"
    gunzip -f "$gz_target"
fi

n_records=$(grep -c '^>' "$fasta_target")
echo
echo "VFDB ($MODE) downloaded to $DEST"
echo "  $n_records virulence factor protein sequences"
