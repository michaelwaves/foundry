# Paper Replication

Replication instructions for *Sparse Autoencoders Find Virulence Features in an All-Atom Protein Diffusion Model*.

All commands assume you are in the repo root. If needed: `cd $(git rev-parse --show-toplevel)`

---

## 1. Install

```bash
# Clone + enter
git clone https://github.com/RosettaCommons/foundry && cd foundry

# Create venv and install foundry + the sae/detectors extras
uv sync
pip install -e sae/
pip install -e detectors/

# Download model weights
foundry install base-models
```

> Requires a GPU with at least 48 GB VRAM (tested on L40).

---

## 2. Collect activations

**RFD3** — partial diffusion (∂t = 5 Å) over 275 SafeProtein + UniProt sequences:

```bash
bash paper_replication/sae_data_rfd3_partial/train_activations/collect_train.sh
```

**RF3** — fold the same sequences:

```bash
bash paper_replication/sae_data_rf3/train_activations/collect_train.sh
```

Activations land in `outputs/sae_data_rfd3_partial/` and `outputs/sae_data_rf3/`.

---

## 3. Train SAEs

One command per (model, block). Takes ~30 min each on an L40.

```bash
# RFD3 blocks 6, 8, 12
for block in 6 8 12; do
  python -m sae.train \
    activations_path=outputs/sae_data_rfd3_partial/train_activations/activations/activations.h5 \
    architecture=matryoshka_batch_top_k \
    hook_name=block${block}
done

# RF3 blocks 12, 16
for block in 12 16; do
  python -m sae.train \
    activations_path=outputs/sae_data_rf3/train_activations/activations/activations.h5 \
    architecture=matryoshka_batch_top_k \
    hook_name=block${block}
done
```

Checkpoints are saved under `outputs/matryoshka_batch_top_k/`.

---

## 4. Build labels and run classifier sweep

```bash
cd paper_replication/classifiers

# Build label CSVs (one-time)
python build_rfd3_labels.py ...   # see classifiers/README.md for full args

# Random 5-fold split
for ds in rfd3_safeprotein rf3_safeprotein rf3_toxinpred3; do
  python split_labels.py --labels $ds/labels.csv --out-dir $ds --n-folds 5
done

# Homology-clustered split (requires mmseqs2)
export CLASSIFIER_RUN_TAG=cluster_stop_overfit
for ds in rfd3_safeprotein rf3_safeprotein rf3_toxinpred3; do
  python cluster_sequences.py --labels $ds/labels.csv --out $ds/clusters.csv
  python split_labels.py --labels $ds/labels.csv --clusters $ds/clusters.csv \
    --out-dir $ds --n-folds 5
done

# Generate configs + sweep
python generate_configs.py
bash sweep_probes.sh
bash sweep_scores.sh

# Aggregate results → results_cluster_stop_overfit/probes.md
python aggregate_metrics.py
```

See [`classifiers/README.md`](classifiers/README.md) for per-cell re-run commands and how to add new datasets.

---

## 5. Figures

```bash
python paper_replication/classifiers/plot_results.py
```

Figures are written to `paper_replication/classifiers/results_cluster_stop_overfit/figures/`.

---

## 6. Steering (preliminary)

```bash
# Compute hazard − benign diff vector
saffron compute_steering_vector \
  inputs=paper_replication/steering/configs/diff_haz_minus_ben.yaml \
  out_dir=outputs/steering/vectors/haz_minus_ben

# Apply during partial diffusion
saffron steer model=rfd3 hooks=rfd3_partial \
  steering=raw_diff_block12 \
  inputs=paper_replication/steering/configs/steer_diff_block12.json \
  out_dir=outputs/steering/runs/benign_inputs_diff_alpha3
```

See [`steering/README.md`](steering/README.md) for the full pipeline (sequence extraction → DTVF scoring).

---

## Directory layout

```
paper_replication/
  sae_data_rfd3_partial/   # activation collection scripts for RFD3
  sae_data_rf3/            # activation collection scripts for RF3
  classifiers/             # label building, splitting, probe sweep, plotting
  steering/                # steering vector computation and application
  benchmarks/              # PPI benchmark runs
```
