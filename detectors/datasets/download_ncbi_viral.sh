#!/usr/bin/env bash
# Download NCBI viral RefSeq protein FASTAs (~106 MB compressed).
# Source: ftp.ncbi.nlm.nih.gov/refseq/release/viral/
# All RefSeq-curated viral proteins, no host/family filter.
#
# For taxonomic filtering use the NCBI 'datasets' CLI instead, e.g.:
#   datasets download virus protein --refseq --host human --filename human-viral.zip
#
# Usage:
#   ./download_ncbi_viral.sh              # default: ./ncbi_viral/
#   ./download_ncbi_viral.sh /dest

set -euo pipefail

DEST="${1:-$(dirname "$0")/ncbi_viral}"
BASE="https://ftp.ncbi.nlm.nih.gov/refseq/release/viral"
FILE="viral.1.protein.faa.gz"

mkdir -p "$DEST"
gz_target="$DEST/$FILE"
fasta_target="${gz_target%.gz}"

if [[ -s "$fasta_target" ]]; then
    echo "skip   $fasta_target (already exists)"
else
    echo "fetch  $BASE/$FILE -> $gz_target  (~106 MB, may take a minute)"
    curl -fL --progress-bar "$BASE/$FILE" -o "$gz_target"
    gunzip -f "$gz_target"
fi

n_records=$(grep -c '^>' "$fasta_target")
echo
echo "NCBI viral RefSeq downloaded to $DEST"
echo "  $n_records viral protein sequences"
