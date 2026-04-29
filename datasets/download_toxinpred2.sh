#!/usr/bin/env bash
# Download ToxinPred 2 protein datasets (~17 MB total) as FASTA files.
# Source: https://webs.iiitd.edu.in/raghava/toxinpred2/stand.html
# Three splits: main, alternate, realistic. The 'realistic' split is closest to
# deployment conditions (large unbalanced negative pool).
#
# Usage:
#   ./download_toxinpred2.sh                       # default: ./toxinpred2/
#   ./download_toxinpred2.sh /path/to/dest         # custom dest

set -euo pipefail

DEST="${1:-$(dirname "$0")/toxinpred2}"
BASE="https://webs.iiitd.edu.in/raghava/toxinpred2/datasets"
SPLITS=(main alternate realistic)
SIGNS=(Positive Negative)

mkdir -p "$DEST"

for split in "${SPLITS[@]}"; do
    for sign in "${SIGNS[@]}"; do
        remote="${sign}_${split}_dataset"
        target="$DEST/${sign,,}_${split}.fasta"
        if [[ -s "$target" ]]; then
            echo "skip   $target (already exists)"
            continue
        fi
        echo "fetch  $BASE/$remote -> $target"
        curl -fsSL "$BASE/$remote" -o "$target"
    done
done

echo
echo "ToxinPred 2 proteins downloaded to $DEST"
for split in "${SPLITS[@]}"; do
    n_pos=$(grep -c '^>' "$DEST/positive_${split}.fasta")
    n_neg=$(grep -c '^>' "$DEST/negative_${split}.fasta")
    printf "  %-10s %5d toxic / %5d non-toxic\n" "$split:" "$n_pos" "$n_neg"
done
