#!/usr/bin/env bash
# Download benign proteins from UniProt: reviewed (Swiss-Prot), NOT toxin,
# NOT virulence, NOT viral. Cursor-paginated FASTA download.
#
# Defaults match SafeBench-Seq's negative-set recipe (NOT KW-0800, non-viral),
# plus a stricter NOT virulence (KW-0843) filter.
#
# Usage:
#   ./download_uniprot_benigns.sh                            # default 10000 records
#   ./download_uniprot_benigns.sh 5000                       # custom count
#   ./download_uniprot_benigns.sh 5000 50 500                # length range 50-500 aa
#   ./download_uniprot_benigns.sh 5000 50 500 /custom/dest

set -euo pipefail

TARGET_COUNT="${1:-10000}"
LEN_MIN="${2:-1}"
LEN_MAX="${3:-2000}"
DEST="${4:-$(dirname "$0")/uniprot_benigns}"
PAGE_SIZE=500

mkdir -p "$DEST"
fasta_target="$DEST/benigns.fasta"
> "$fasta_target"

QUERY="reviewed:true+NOT+keyword:KW-0800+NOT+keyword:KW-0843+NOT+taxonomy_id:10239+AND+length:%5B${LEN_MIN}%20TO%20${LEN_MAX}%5D"
URL="https://rest.uniprot.org/uniprotkb/search?query=${QUERY}&format=fasta&size=${PAGE_SIZE}"

echo "fetch  UniProt benigns (target=${TARGET_COUNT}, length=${LEN_MIN}-${LEN_MAX})"

next_url="$URL"
total=0
while [[ -n "$next_url" ]] && (( total < TARGET_COUNT )); do
    headers=$(mktemp)
    curl -fsSLg -D "$headers" "$next_url" >> "$fasta_target"
    page_count=$(grep -c '^>' "$fasta_target" || true)
    new_total=$((page_count))
    echo "  fetched $((new_total - total)) records (total=$new_total)"
    total=$new_total
    next_url=$(awk -F'[<>]' '/^[Ll]ink:.*rel="next"/ {print $2; exit}' "$headers" || true)
    rm -f "$headers"
done

echo
echo "UniProt benigns downloaded to $DEST"
echo "  $total benign protein sequences"
