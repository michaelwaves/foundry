#!/usr/bin/env bash
# Run RFD3 partial-diffusion activation collection on a sources.csv
# (SafeProtein hazards by default). Each entry is partially noised to PARTIAL_T
# Å and denoised — activations during the rebuild are conditioned on the source.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SOURCES="${SOURCES:-$HERE/sources.csv}"
INPUTS="$HERE/train_inputs.json"
OUT_DIR="$HERE/train_activations"
PARTIAL_T="${PARTIAL_T:-5.0}"

if [[ ! -s "$SOURCES" ]]; then
    echo "missing $SOURCES — run fetch_safeprotein_pdbs.sh first (or write your own)" >&2
    exit 1
fi

echo "building/refreshing $INPUTS (partial_t=$PARTIAL_T Å)..."
python "$HERE/build_inputs.py" \
    --sources "$SOURCES" \
    --out "$INPUTS" \
    --partial-t "$PARTIAL_T"

echo "running saffron collect -> $OUT_DIR"
saffron collect \
    model=rfd3 \
    inputs="$INPUTS" \
    out_dir="$OUT_DIR"\
    diffusion_batch_size=2

