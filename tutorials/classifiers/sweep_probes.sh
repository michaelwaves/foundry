#!/usr/bin/env bash
# Run detect fit + detect evaluate for every configs/<dataset>/fit_*.yaml.
# Outputs:
#   outputs/classifiers/<dataset>/fit/<model>_<hook>_<extractor>/   (bundle, train metrics)
#   outputs/classifiers/<dataset>/eval/<model>_<hook>_<extractor>/  (held-out metrics)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT_ROOT="$ROOT/outputs/classifiers"

shopt -s nullglob
for fit_cfg in "$HERE"/configs/*/fit_*.yaml; do
    dataset="$(basename "$(dirname "$fit_cfg")")"
    model="${dataset%%_*}"
    cell="$(basename "$fit_cfg" .yaml)"
    cell="${cell#fit_}"
    fit_out="$OUT_ROOT/$dataset/fit/${model}_${cell}"
    eval_out="$OUT_ROOT/$dataset/eval/${model}_${cell}"
    eval_cfg="$HERE/configs/$dataset/eval_${cell}.yaml"

    echo "=== detect fit: $dataset / ${model}_${cell} ==="
    detect fit inputs="$fit_cfg" out_dir="$fit_out"

    if [[ -f "$eval_cfg" ]]; then
        echo "=== detect evaluate: $dataset / ${model}_${cell} ==="
        detect evaluate inputs="$eval_cfg" out_dir="$eval_out"
    else
        echo "skip evaluate: no $eval_cfg"
    fi
done
