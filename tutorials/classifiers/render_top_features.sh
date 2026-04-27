#!/usr/bin/env bash
# Read top_features.csv, render PyMOL .pml + PNG for the top-N hazard-firing
# SAE features per (dataset, hook). Requires pymol on PATH for the PNG step;
# without it you'll still get .pml scripts that you can render anywhere.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TOP_FEATURES_CSV="$HERE/results/top_features.csv"
TOP_N="${TOP_N:-5}"             # features per (dataset, hook) to render
TOP_DESIGNS="${TOP_DESIGNS:-3}"  # designs per feature
TOP_RESIDUES="${TOP_RESIDUES:-5}"
DEVICE="${DEVICE:-cpu}"

# Map dataset -> (activations_h5, metadata_dir, sae_root)
declare -A ACT
declare -A META
declare -A SAE
ACT[rfd3_safeprotein]="$ROOT/tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5"
META[rfd3_safeprotein]="$ROOT/tutorials/sae_data_rfd3_partial/train_activations"
SAE[rfd3_safeprotein]="$ROOT/outputs/sae/2026-04-26_15-38-55/train"
# rf3 cells aren't supported by visualize_features.py yet (no metadata pickles
# saved by saffron-collect for rf3 — only rfd3 dumps cif.gz). Skip them.

# Pick top-N hazard-firing SAE features per (dataset, hook) from the parquet.
# (top_features.md also has benign-firing features; for steering interpretation
# we focus on hazard-firing, AUROC > 0.5.)
python - <<'PY' > /tmp/feature_jobs.tsv
import pandas as pd
import os
df = pd.read_csv(os.environ['TOP_FEATURES_CSV'])
df = df[(df.extractor == 'sae_encode') & (df.dataset == 'rfd3_safeprotein') & (df.auroc > 0.5)]
top_n = int(os.environ['TOP_N'])
for (ds, hook), g in df.groupby(['dataset', 'hook']):
    feats = ','.join(str(int(f)) for f in g.sort_values('auroc', ascending=False).head(top_n).feature_id)
    if feats:
        print(f"{ds}\t{hook}\t{feats}")
PY

while IFS=$'\t' read -r ds hook feats; do
    echo "=== $ds / $hook : features $feats ==="
    out="$ROOT/outputs/classifiers/viz/${ds}_${hook}"
    python "$HERE/visualize_features.py" \
        --checkpoint "${SAE[$ds]}/$hook/final.pt" \
        --activations "${ACT[$ds]}" \
        --metadata-dir "${META[$ds]}" \
        --hook "$hook" \
        --features "$feats" \
        --top-designs "$TOP_DESIGNS" \
        --top-residues "$TOP_RESIDUES" \
        --device "$DEVICE" \
        --out "$out"

    if command -v pymol >/dev/null 2>&1; then
        echo "rendering PNGs with pymol..."
        for pml in "$out"/*.pml; do
            pymol -cq "$pml" 2>&1 | tail -1
        done
    else
        echo "pymol not on PATH — only .pml scripts written; install pymol then run:"
        echo "  for pml in $out/*.pml; do pymol -cq \"\$pml\"; done"
    fi
done < /tmp/feature_jobs.tsv
