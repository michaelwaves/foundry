#!/usr/bin/env bash
# Build/refresh train_inputs.json from the SafeProtein hazards + UniProt benigns
# sources.csv (the same set RFD3 partial-diffusion saw), then run saffron collect
# with the RF3 hooks. Sequence per entry is extracted from the PDB so design_ids
# match those used by tutorials/sae_data_rfd3_partial — enabling apples-to-apples
# RF3 vs RFD3 probing on the same labels.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SOURCES="${SOURCES:-$HERE/../../sae_data_rfd3_partial/sources.csv}"
INPUTS="$HERE/train_inputs.json"
OUT_DIR="$HERE/train_activations"
SUBSAMPLE="${SUBSAMPLE:-}"

if [[ ! -s "$SOURCES" ]]; then
    echo "missing $SOURCES — run tutorials/sae_data_rfd3_partial/fetch_safeprotein_pdbs.sh first" >&2
    exit 1
fi

echo "building/refreshing $INPUTS from $SOURCES..."
python "$HERE/build_inputs.py" \
    --sources "$SOURCES" \
    --out "$INPUTS" \
    ${SUBSAMPLE:+--subsample "$SUBSAMPLE"}

echo "running saffron collect -> $OUT_DIR"
saffron collect \
    model=rf3 \
    inputs="$INPUTS" \
    out_dir="$OUT_DIR"
