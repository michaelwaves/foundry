RUN_ROOT=/mnt/nw/home/m.yu/repos/foundry/outputs/sae/$(date +%Y-%m-%d_%H-%M-%S)
DATA_DIR=/mnt/nw/home/m.yu/repos/foundry/tutorials/sae_data
TRAIN_ACTIVATIONS=$DATA_DIR/train_activations_2/activations/activations.h5

#IMPORTANT: these hook names must exist in the TRAIN_ACTIVATIONS activations.h5 file
for HOOK in token_initializer_outputs block6 block8 block12; do
    TRAIN_DIR=$RUN_ROOT/train/$HOOK
    echo "===training hook $HOOK ==="
    saffron train \
        activations_path="$TRAIN_ACTIVATIONS" \
        hook_name="$HOOK" \
        out_dir="$TRAIN_DIR"
        use_wanb=true

done

exit 0