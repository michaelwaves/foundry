#!/usr/bin/env bash
# Run detect score for every configs/<dataset>/score_<hook>_<extractor>.yaml.
# Outputs land at outputs/classifiers/<dataset>/score/<model>_<hook>_<extractor>/.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT_ROOT="$ROOT/outputs/classifiers"

shopt -s nullglob
for cfg in "$HERE"/configs/*/score_*.yaml; do
    dataset="$(basename "$(dirname "$cfg")")"
    model="${dataset%%_*}"
    cell="$(basename "$cfg" .yaml)"
    cell="${cell#score_}"
    out="$OUT_ROOT/$dataset/score/${model}_${cell}"
    echo "=== detect score: $dataset / ${model}_${cell} ==="
    detect score inputs="$cfg" out_dir="$out"
done
