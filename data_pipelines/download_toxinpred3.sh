#!/usr/bin/env bash
# Download ToxinPred 3.0 train/test peptide datasets (~265 KB total).
# Source: https://github.com/raghavagps/toxinpred3
# Each file is one peptide sequence per line (no header).
#
# Usage:
#   ./download_toxinpred.sh                       # default: ./toxinpred3/
#   ./download_toxinpred.sh /path/to/dest         # custom dest

set -euo pipefail

DEST="${1:-$(dirname "$0")/toxinpred3}"
BASE="https://raw.githubusercontent.com/raghavagps/toxinpred3/main/dataset"
FILES=(train_pos.csv train_neg.csv test_pos.csv test_neg.csv)

mkdir -p "$DEST"

for file in "${FILES[@]}"; do
    target="$DEST/$file"
    if [[ -s "$target" ]]; then
        echo "skip   $target (already exists)"
        continue
    fi
    echo "fetch  $BASE/$file -> $target"
    curl -fsSL "$BASE/$file" -o "$target"
done

n_pos_train=$(wc -l < "$DEST/train_pos.csv")
n_neg_train=$(wc -l < "$DEST/train_neg.csv")
n_pos_test=$(wc -l < "$DEST/test_pos.csv")
n_neg_test=$(wc -l < "$DEST/test_neg.csv")

echo
echo "ToxinPred 3.0 peptides downloaded to $DEST"
echo "  train: $n_pos_train toxic / $n_neg_train non-toxic"
echo "  test:  $n_pos_test toxic / $n_neg_test non-toxic"
