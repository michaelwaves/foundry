#!/usr/bin/env bash
# Generate RF3 input JSON from ToxinPred 3 train splits, then run saffron collect
# with the four hooks defined in hooks.yaml. Outputs go to train_activations/.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOX_DIR="$HERE/../../detectors/datasets/toxinpred3"
INPUTS="$HERE/train_inputs.json"
HOOKS="$HERE/hooks.yaml"
OUT_DIR="$HERE/train_activations"
SUBSAMPLE="${SUBSAMPLE:-100}"

if [[ ! -f "$TOX_DIR/train_pos.csv" || ! -f "$TOX_DIR/train_neg.csv" ]]; then
    echo "missing ToxinPred CSVs — run detectors/datasets/download_toxinpred.sh first" >&2
    exit 1
fi

if [[ ! -s "$INPUTS" ]]; then
    echo "building $INPUTS (subsample=$SUBSAMPLE per class)..."
    python "$HERE/build_inputs.py" \
        --positive "$TOX_DIR/train_pos.csv" \
        --negative "$TOX_DIR/train_neg.csv" \
        --out "$INPUTS" \
        --subsample "$SUBSAMPLE"
fi

echo "running saffron collect -> $OUT_DIR"
saffron collect \
    model=rf3 \
    inputs="$INPUTS" \
    out_dir="$OUT_DIR" \
    hooks="$HOOKS"
