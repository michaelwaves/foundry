#!/usr/bin/env bash
# Run detect score for every configs<_tag>/<dataset>/score_<hook>_<extractor>.yaml.
# CLASSIFIER_RUN_TAG (e.g. "cluster") routes to configs_<tag>/ and
# outputs/classifiers_<tag>/ so multiple runs can coexist.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SUFFIX="${CLASSIFIER_RUN_TAG:+_$CLASSIFIER_RUN_TAG}"
CONFIGS_DIR="$HERE/configs${SUFFIX}"
OUT_ROOT="$ROOT/outputs/classifiers${SUFFIX}"

shopt -s nullglob
for cfg in "$CONFIGS_DIR"/*/score_*.yaml; do
    dataset="$(basename "$(dirname "$cfg")")"
    model="${dataset%%_*}"
    cell="$(basename "$cfg" .yaml)"
    cell="${cell#score_}"
    out="$OUT_ROOT/$dataset/score/${model}_${cell}"
    echo "=== detect score: $dataset / ${model}_${cell} ==="
    detect score inputs="$cfg" out_dir="$out"
done
