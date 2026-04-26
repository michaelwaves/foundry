RUN_ROOT=/mnt/nw/home/m.yu/repos/foundry/outputs/sae/2026-04-26_15-23-45
TRAIN_ACTIVATIONS=/mnt/nw/home/m.yu/repos/foundry/tutorials/sae_data_rf3/train_activations/activations/activations.h5

for HOOK in block12; do
    TRAIN_DIR=$RUN_ROOT/train/$HOOK
    echo "---training hook $HOOK----"
    saffron train \
        activations_path="$TRAIN_ACTIVATIONS"\
        hook_name="$HOOK"\
        out_dir="$TRAIN_DIR"\
        use_wandb=true

done 

exit 0