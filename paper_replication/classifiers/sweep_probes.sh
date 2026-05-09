#!/usr/bin/env bash
# Run detect fit + detect evaluate for every configs<_tag>/<dataset>/fit_*.yaml.
# CLASSIFIER_RUN_TAG (e.g. "cluster") routes to configs_<tag>/ and
# outputs/classifiers_<tag>/ so multiple runs can coexist.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SUFFIX="${CLASSIFIER_RUN_TAG:+_$CLASSIFIER_RUN_TAG}"
CONFIGS_DIR="$HERE/configs${SUFFIX}"
OUT_ROOT="$ROOT/outputs/classifiers${SUFFIX}"

shopt -s nullglob
for fit_cfg in "$CONFIGS_DIR"/*/fit_*.yaml; do
    dataset="$(basename "$(dirname "$fit_cfg")")"
    model="${dataset%%_*}"
    cell="$(basename "$fit_cfg" .yaml)"
    cell="${cell#fit_}"
    fit_out="$OUT_ROOT/$dataset/fit/${model}_${cell}"
    eval_out="$OUT_ROOT/$dataset/eval/${model}_${cell}"
    eval_cfg="$CONFIGS_DIR/$dataset/eval_${cell}.yaml"

    echo "=== detect fit: $dataset / ${model}_${cell} ==="
    detect fit inputs="$fit_cfg" out_dir="$fit_out"

    if [[ -f "$eval_cfg" ]]; then
        echo "=== detect evaluate: $dataset / ${model}_${cell} ==="
        detect evaluate inputs="$eval_cfg" out_dir="$eval_out"
    else
        echo "skip evaluate: no $eval_cfg"
    fi
done
