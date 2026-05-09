FOUNDRY_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$FOUNDRY_ROOT"
RUN_ROOT=outputs/sae/$(date +%Y-%m-%d_%H-%M-%S)
DATA_DIR=tutorials/sae_data_rfd3_partial
TRAIN_ACTIVATIONS=$DATA_DIR/train_activations/activations/activations.h5

#IMPORTANT: these hook names must exist in the TRAIN_ACTIVATIONS activations.h5 file
for HOOK in token_initializer_outputs block6 block8 block12; do
    TRAIN_DIR=$RUN_ROOT/train/$HOOK
    echo "===training hook $HOOK ==="
    saffron train \
        activations_path="$TRAIN_ACTIVATIONS" \
        hook_name="$HOOK" \
        out_dir="$TRAIN_DIR" \
        use_wandb=true

done

exit 0