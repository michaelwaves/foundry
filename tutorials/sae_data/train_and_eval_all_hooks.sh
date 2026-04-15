#!/usr/bin/env bash
set -euo pipefail

DATA_DIR=/mnt/nw/home/m.yu/repos/foundry/tutorials/sae_data
TRAIN_H5=$DATA_DIR/train_activations/activations.h5
TEST_H5=$DATA_DIR/test_activations/activations.h5
TEST_META=$DATA_DIR/test_activations
RUN_ROOT=/mnt/nw/home/m.yu/repos/foundry/outputs/sae/$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p "$RUN_ROOT"
echo "run root: $RUN_ROOT"

for HOOK in block6 block12 block17; do
    TRAIN_DIR=$RUN_ROOT/train/$HOOK
    EVAL_DIR=$RUN_ROOT/eval/$HOOK

    echo "=== train $HOOK ==="
    saffron train \
        activations_path="$TRAIN_H5" \
        hook_name="$HOOK" \
        out_dir="$TRAIN_DIR" \
        use_wandb=true

    echo "=== eval $HOOK ==="
    saffron eval \
        checkpoint_path="$TRAIN_DIR/final.pt" \
        hook_name="$HOOK" \
        activations_path="$TEST_H5" \
        metadata_dir="$TEST_META" \
        out_dir="$EVAL_DIR"
done

echo "=== done: $RUN_ROOT ==="

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    scancel "$SLURM_JOB_ID"
else
    exit 0
fi
