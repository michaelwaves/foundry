#!/usr/bin/env bash
# Build/refresh train_inputs.json from ToxinPred 3 train splits, then run
# saffron collect with the hooks embedded in run_config (preserved across rebuilds).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOX_DIR="$HERE/../../detectors/datasets/toxinpred3"
INPUTS="$HERE/train_inputs.json"
OUT_DIR="$HERE/train_activations"
SUBSAMPLE="${SUBSAMPLE:-100}"

if [[ ! -f "$TOX_DIR/train_pos.csv" || ! -f "$TOX_DIR/train_neg.csv" ]]; then
    echo "missing ToxinPred CSVs — run detectors/datasets/download_toxinpred.sh first" >&2
    exit 1
fi

echo "building/refreshing $INPUTS (subsample=$SUBSAMPLE per class)..."
python "$HERE/build_inputs.py" \
    --positive "$TOX_DIR/train_pos.csv" \
    --negative "$TOX_DIR/train_neg.csv" \
    --out "$INPUTS" \
    --subsample "$SUBSAMPLE"

echo "running saffron collect -> $OUT_DIR"
saffron collect \
    model=rf3 \
    inputs="$INPUTS" \
    out_dir="$OUT_DIR"
