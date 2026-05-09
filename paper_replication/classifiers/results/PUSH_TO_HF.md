# Pushing all artifacts to HuggingFace

Paste-able from your shell with the foundry venv active. Pushes 9 repos
(~36 GB total) under `michaelwaves/`. Uses `hf upload-large-folder` with the
rust-based parallel uploader so the multi-GB ones go fast and resume on
interruption.

## 0. Setup + auth

```bash
uv pip install -U "huggingface_hub[cli]" hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1     # turbo upload via the rust client
hf auth whoami                          # should print michaelwaves
```

## 1. Small results datasets (KB)

```bash
for variant in random:results_stop_overfitting clustered:results_cluster_stop_overfit; do
  tag="${variant%:*}"; src="${variant#*:}"
  repo="michaelwaves/saeber-virulence-probes-${tag}"
  hf repo create "$repo" --repo-type dataset -y
  hf upload "$repo" "tutorials/classifiers/$src" \
    . --repo-type dataset --commit-message "initial upload"
done
```

## 2. Activation datasets (~11 GB across 3 repos)

```bash
declare -A ACT=(
  [saeber-rfd3-safeprotein-activations]=tutorials/sae_data_rfd3_partial/train_activations
  [saeber-rf3-safeprotein-activations]=tutorials/sae_data_rf3/uniprot/train_activations
)
for name in "${!ACT[@]}"; do
  hf repo create "michaelwaves/$name" --repo-type dataset -y
  hf upload-large-folder "michaelwaves/$name" "${ACT[$name]}" --repo-type dataset
done

# rf3 toxinpred has split train+test dirs — bundle as one local tree first
TMP_RF3_TOX=/tmp/saeber-rf3-toxinpred3-activations
mkdir -p "$TMP_RF3_TOX"
ln -snf tutorials/sae_data_rf3/train_activations "$TMP_RF3_TOX/train_activations"
ln -snf tutorials/sae_data_rf3/test_activations  "$TMP_RF3_TOX/test_activations"
hf repo create michaelwaves/saeber-rf3-toxinpred3-activations --repo-type dataset -y
hf upload-large-folder michaelwaves/saeber-rf3-toxinpred3-activations "$TMP_RF3_TOX" --repo-type dataset
```

## 3. SAE model repos (~5 GB across 3 repos)

```bash
declare -A SAE=(
  [saeber-rfd3-safeprotein-sae]=outputs/sae/2026-04-26_15-38-55/train
  [saeber-rf3-toxinpred3-sae]=outputs/sae/2026-04-26_15-23-45/train
  [saeber-rf3-safeprotein-sae]=outputs/sae/2026-04-26_22-03-07/train
)
for name in "${!SAE[@]}"; do
  hf repo create "michaelwaves/$name" --repo-type model -y
  hf upload-large-folder "michaelwaves/$name" "${SAE[$name]}" --repo-type model
done
```

## 4. Probe bundles (~20 GB, biggest one)

Both random and cluster sweeps bundled into one repo as `random/` and `cluster/` subfolders.

```bash
TMP_PROBES=/tmp/saeber-virulence-probes
mkdir -p "$TMP_PROBES"
ln -snf outputs/classifiers_stop_overfitting   "$TMP_PROBES/random"
ln -snf outputs/classifiers_cluster_stop_overfit "$TMP_PROBES/cluster"
hf repo create michaelwaves/saeber-virulence-probes --repo-type model -y
hf upload-large-folder michaelwaves/saeber-virulence-probes "$TMP_PROBES" --repo-type model
```

## 5. register.csv

```bash
cat > tutorials/classifiers/results/register.csv <<'EOF'
artifact_type,name,hf_repo,source_local_path,size,note
dataset,virulence-probes-random,michaelwaves/saeber-virulence-probes-random,tutorials/classifiers/results_stop_overfitting,24K,5-fold CV probe metrics on random splits
dataset,virulence-probes-homology-clustered,michaelwaves/saeber-virulence-probes-homology-clustered,tutorials/classifiers/results_cluster_stop_overfit,584K,5-fold CV probe metrics on mmseqs2 30%-identity cluster splits
dataset,rfd3-safeprotein-activations,michaelwaves/saeber-rfd3-safeprotein-activations,tutorials/sae_data_rfd3_partial/train_activations,4.9G,RFD3 partial-diffusion activations + 580 cif.gz/json structural metadata
dataset,rf3-toxinpred3-activations,michaelwaves/saeber-rf3-toxinpred3-activations,tutorials/sae_data_rf3/{train,test}_activations,2.9G,RF3 folding activations on ToxinPred3 train+test
dataset,rf3-safeprotein-activations,michaelwaves/saeber-rf3-safeprotein-activations,tutorials/sae_data_rf3/uniprot/train_activations,3.3G,RF3 folding activations on SafeProtein/UniProt
model,rfd3-safeprotein-sae,michaelwaves/saeber-rfd3-safeprotein-sae,outputs/sae/2026-04-26_15-38-55/train,2.0G,Matryoshka BatchTopK SAE per RFD3 hook (block6/8/12/token_initializer_outputs)
model,rf3-toxinpred3-sae,michaelwaves/saeber-rf3-toxinpred3-sae,outputs/sae/2026-04-26_15-23-45/train,1.5G,Matryoshka BatchTopK SAE per RF3 hook (block12/16/to_si/to_r_update)
model,rf3-safeprotein-sae,michaelwaves/saeber-rf3-safeprotein-sae,outputs/sae/2026-04-26_22-03-07/train,1.5G,Matryoshka BatchTopK SAE per RF3 hook trained on SafeProtein/UniProt activations
model,virulence-probes,michaelwaves/saeber-virulence-probes,outputs/classifiers_{stop_overfitting,cluster_stop_overfit},20G,All 200 LR probe bundles under random/ and cluster/ subfolders
EOF
```

## Notes

- **`HF_HUB_ENABLE_HF_TRANSFER=1`** + `hf_transfer` package give you the rust-based parallel uploader, much faster than the default Python one for multi-GB pushes. Essential for the 20 GB probes repo.
- **`upload-large-folder`** chunks the upload, resumes on interruption, and parallelizes uploads of large files.
- **Each repo created with `-y`** to skip the interactive confirm.
- **Probe bundles + ToxinPred3 activations bundled via symlinks** (`ln -snf`) into `/tmp/...` so HF sees one tree without copying 20 GB.
- **READMEs not auto-generated** — add per repo afterward if you want descriptions:
  ```bash
  hf upload michaelwaves/saeber-virulence-probes README.md README.md --repo-type model
  ```
- **If a push fails partway**: re-run the same `upload-large-folder` command, it picks up where it left off.
- **Realistic upload time**: ~1–2 hours total depending on bandwidth.
