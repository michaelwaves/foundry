# Classifier sweep

Probe SAE features (and raw activations) for toxic/viral classification across
`{rfd3_safeprotein, rf3_safeprotein, rf3_toxinpred3} × {hooks} × {identity, sae_encode}`.

The harness emits 5-fold CV by default and supports two split modes:
- **Random stratified** — fast, but paralog leakage inflates AUROC.
- **Cluster-aware** (`--clusters`) — homology-clean via MMseqs2 at 30% identity.

A single env var `CLASSIFIER_RUN_TAG` keeps multiple runs (e.g. random vs
cluster) on disk side-by-side without clobbering each other.

## Pre-requisites

Activations + SAEs are produced upstream:
- `tutorials/sae_data_rfd3_partial/{collect_train.sh, train_all_hooks.sh}`
- `tutorials/sae_data_rf3/{collect_train.sh, train_all_hooks.sh}`
- `tutorials/sae_data_rf3/uniprot/{collect_train.sh, train_all_hooks.sh}`

For homology-clustered splits, install MMseqs2 (no sudo needed):
```bash
mkdir -p ~/tools && cd ~/tools
wget https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz
tar -xzf mmseqs-linux-avx2.tar.gz
~/tools/mmseqs/bin/mmseqs --help
```

## End-to-end (random k-fold — default)

```bash
# Run from the repo root

# 1. Build labels.csv per dataset (one-time; design_id keying differs per cell)
python tutorials/classifiers/build_rfd3_labels.py \
  --activations tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5 \
  --hook block6 --positive-prefix hazard_ --negative-prefix benign_ \
  --inputs-stem train_inputs \
  --out tutorials/classifiers/rfd3_safeprotein/labels.csv

python tutorials/classifiers/build_rfd3_labels.py \
  --activations tutorials/sae_data_rf3/train_activations/activations/activations.h5 \
  --hook block12 --positive-prefix train_pos_ --negative-prefix train_neg_ \
  --inputs-stem '' \
  --out tutorials/classifiers/rf3_toxinpred3/labels.csv

# rf3_safeprotein labels are a rekey of the rfd3 labels (same proteins, same split)
python -c "
import pandas as pd
df = pd.read_csv('tutorials/classifiers/rfd3_safeprotein/labels.csv')
pd.DataFrame({'design_id': df.source_id, 'label': df.label, 'source_id': df.source_id}) \
  .to_csv('tutorials/classifiers/rf3_safeprotein/labels.csv', index=False)
"

# 2. Stratified 5-fold split per dataset (random)
for ds in rfd3_safeprotein rf3_safeprotein rf3_toxinpred3; do
  python tutorials/classifiers/split_labels.py \
    --labels  tutorials/classifiers/$ds/labels.csv \
    --out-dir tutorials/classifiers/$ds --n-folds 5
done

# 3. Generate configs (CLASSIFIER_DEVICE=cpu if no GPU)
python tutorials/classifiers/generate_configs.py

# 4. Sweeps
bash tutorials/classifiers/sweep_scores.sh   # Q2 — per-feature attribution
bash tutorials/classifiers/sweep_probes.sh   # Q1 — fit + evaluate, all folds

# 5. Aggregate (writes probes.md / top_features.md / per-fold CSVs)
python tutorials/classifiers/aggregate_metrics.py
# results land at tutorials/classifiers/results/
```

## End-to-end (cluster-aware k-fold)

Set `CLASSIFIER_RUN_TAG=cluster` and rerun steps 2–5. Outputs route to
`configs_cluster/`, `outputs/classifiers_cluster/`, `tutorials/classifiers/results_cluster/`.
The random run is preserved.

```bash
# 1. Build clusters.csv per dataset
for ds in rfd3_safeprotein rf3_safeprotein; do
  python tutorials/classifiers/cluster_sequences.py \
    --labels tutorials/classifiers/$ds/labels.csv \
    --inputs tutorials/sae_data_rfd3_partial/train_inputs.json \
    --out    tutorials/classifiers/$ds/clusters.csv
done
python tutorials/classifiers/cluster_sequences.py \
  --labels tutorials/classifiers/rf3_toxinpred3/labels.csv \
  --inputs tutorials/sae_data_rf3/train_inputs.json \
  --out    tutorials/classifiers/rf3_toxinpred3/clusters.csv

# 2. Cluster-aware 5-fold split (writes labels_fold*_train_cluster.csv etc)
export CLASSIFIER_RUN_TAG=cluster
for ds in rfd3_safeprotein rf3_safeprotein rf3_toxinpred3; do
  python tutorials/classifiers/split_labels.py \
    --labels   tutorials/classifiers/$ds/labels.csv \
    --clusters tutorials/classifiers/$ds/clusters.csv \
    --out-dir  tutorials/classifiers/$ds --n-folds 5
done

# 3-5. Same as above, env var routes everything
python tutorials/classifiers/generate_configs.py
bash   tutorials/classifiers/sweep_scores.sh
bash   tutorials/classifiers/sweep_probes.sh
python tutorials/classifiers/aggregate_metrics.py
# results land at tutorials/classifiers/results_cluster/

unset CLASSIFIER_RUN_TAG
```

## Compare random vs cluster

After both runs:
```bash
ls tutorials/classifiers/results          # probes.md from random k-fold
ls tutorials/classifiers/results_cluster  # probes.md from cluster k-fold
```
Each `probes.md` has `eval_auroc_mean` / `eval_auroc_std` / `n_folds` per cell.
Cluster-aware AUROCs typically drop 0.05–0.15 vs random — that drop is the
paralog-leakage you were getting for free before.

## Re-run a single cell

```bash
detect score    inputs=tutorials/classifiers/configs/rfd3_safeprotein/score_block6_sae_encode.yaml \
                out_dir=outputs/classifiers/rfd3_safeprotein/score/rfd3_block6_sae_encode

detect fit      inputs=tutorials/classifiers/configs/rfd3_safeprotein/fit_block6_sae_encode__fold0.yaml \
                out_dir=outputs/classifiers/rfd3_safeprotein/fit/rfd3_block6_sae_encode__fold0

detect evaluate inputs=tutorials/classifiers/configs/rfd3_safeprotein/eval_block6_sae_encode__fold0.yaml \
                out_dir=outputs/classifiers/rfd3_safeprotein/eval/rfd3_block6_sae_encode__fold0
```

## Adding a new dataset

Edit the `DATASETS` dict in `generate_configs.py` (one entry: activations h5,
labels dir, SAE checkpoint root, hook list). Then build labels + run steps 2–5.
