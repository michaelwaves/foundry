# Classifier sweep

```bash
# 1. Build labels from each activations.h5 (class derived from design_id prefix)
python tutorials/classifiers/build_rfd3_labels.py \
  --activations tutorials/sae_data_rfd3_partial/train_activations/activations/activations.h5 \
  --hook block6 \
  --positive-prefix hazard_ --negative-prefix benign_ \
  --inputs-stem train_inputs \
  --out tutorials/classifiers/rfd3_safeprotein/labels.csv

python tutorials/classifiers/build_rfd3_labels.py \
  --activations tutorials/sae_data_rf3/train_activations/activations/activations.h5 \
  --hook block12 \
  --positive-prefix train_pos_ --negative-prefix train_neg_ \
  --inputs-stem '' \
  --out tutorials/classifiers/rf3_toxinpred3/labels_train.csv

python tutorials/classifiers/build_rfd3_labels.py \
  --activations tutorials/sae_data_rf3/test_activations/activations/activations.h5 \
  --hook block12 \
  --positive-prefix test_pos_ --negative-prefix test_neg_ \
  --inputs-stem '' \
  --out tutorials/classifiers/rf3_toxinpred3/labels_test.csv

cp tutorials/classifiers/rf3_toxinpred3/labels_train.csv tutorials/classifiers/rf3_toxinpred3/labels.csv

# 2. Stratified train/test split for RFD3 (one h5, two label files)
python tutorials/classifiers/split_labels.py \
  --labels tutorials/classifiers/rfd3_safeprotein/labels.csv \
  --train  tutorials/classifiers/rfd3_safeprotein/labels_train.csv \
  --test   tutorials/classifiers/rfd3_safeprotein/labels_test.csv \
  --test-fraction 0.2

# 3. Generate score / fit / eval yamls (set CLASSIFIER_DEVICE=cpu if no GPU)
CLASSIFIER_DEVICE=cuda:0 python tutorials/classifiers/generate_configs.py

# 4. Q2 — top SAE features per (dataset, hook)
bash tutorials/classifiers/sweep_scores.sh

# 5. Q1 — fit + evaluate logistic probes per (dataset, hook, extractor)
bash tutorials/classifiers/sweep_probes.sh

# 6. Aggregate everything into markdown tables
python tutorials/classifiers/aggregate_metrics.py \
  --sweep-root outputs/classifiers \
  --out tutorials/classifiers/results
```

## Pre-requisites

```bash
# Activations + SAEs (already done):
#   tutorials/sae_data_rfd3_partial/{collect_train.sh, train_all_hooks.sh}
#   tutorials/sae_data_rf3/{collect_train.sh, train_all_hooks.sh}
#
# RF3 x SafeProtein/UniProt cell (in progress):
bash tutorials/sae_data_rf3/uniprot/collect_train.sh
bash tutorials/sae_data_rf3/uniprot/train_all_hooks.sh
# then add an "rf3_safeprotein" entry to DATASETS in generate_configs.py
```

## Re-run a single cell

```bash
detect score    inputs=tutorials/classifiers/configs/rfd3_safeprotein/score_block6_sae_encode.yaml \
                out_dir=outputs/classifiers/rfd3_safeprotein/score/rfd3_block6_sae_encode

detect fit      inputs=tutorials/classifiers/configs/rfd3_safeprotein/fit_block6_sae_encode.yaml \
                out_dir=outputs/classifiers/rfd3_safeprotein/fit/rfd3_block6_sae_encode

detect evaluate inputs=tutorials/classifiers/configs/rfd3_safeprotein/eval_block6_sae_encode.yaml \
                out_dir=outputs/classifiers/rfd3_safeprotein/eval/rfd3_block6_sae_encode
```
