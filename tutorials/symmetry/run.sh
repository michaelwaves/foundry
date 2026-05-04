#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

COMMON=(
    inference_sampler.kind=symmetry
    diffusion_batch_size=1
    n_batches=2
)

for spec in uncond_cyclic uncond_dihedral motif_C2_unindexed motif_C2_indexed_HEM motif_C3_DNA; do
    rfd3 design \
        inputs="${spec}.json" \
        out_dir="outputs/${spec}" \
        "${COMMON[@]}"
done
