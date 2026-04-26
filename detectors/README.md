# detectors

Toxic/viral classifiers over RFD3 SAE features. Three orthogonal axes:
**FeatureExtractor** (raw or SAE-encoded) × **Scorer** (AUROC) × **Detector** (logistic / top-feature threshold).

See [`plan.md`](plan.md) for the full design. Lit review of toxic/viral datasets in
[`datasets/lit_review.csv`](datasets/lit_review.csv).

## Datasets

**ToxinPred 3.0 — peptides** (4,414 toxic + 4,414 non-toxic train; 1,104 + 1,104 test;
~265 KB total). One sequence per line, no header.

```bash
detectors/datasets/download_toxinpred.sh                    # → detectors/datasets/toxinpred3/
detectors/datasets/download_toxinpred.sh /custom/dest       # custom location
```

**ToxinPred 2 — proteins** (3 splits × pos/neg, ~17 MB total). Real FASTA format.
The `realistic` split has a heavily unbalanced negative pool (1,924 pos / 19,240 neg)
and is closest to deployment conditions.

```bash
detectors/datasets/download_toxinpred2.sh                   # → detectors/datasets/toxinpred2/
detectors/datasets/download_toxinpred2.sh /custom/dest
```

**VFDB — bacterial virulence factors**. Set A is the experimentally verified core
(~4,600 proteins, 1.3 MB gz); Set B is the full set including predictions (~5.6 MB gz).

```bash
detectors/datasets/download_vfdb.sh              # core (set A) → detectors/datasets/vfdb/
detectors/datasets/download_vfdb.sh full         # full (set B)
```

**NCBI viral RefSeq — all curated viral proteins** (~106 MB compressed). The canonical
viral protein resource. For taxon/host filtering, use NCBI's `datasets` CLI instead.

```bash
detectors/datasets/download_ncbi_viral.sh        # → detectors/datasets/ncbi_viral/
```

**SafeProtein hazard set** — the positive class used by SafeBench-Seq. 429 hazardous
proteins with full sequences + PDB metadata + conservation scores. Sequences are
distributed directly (so no UniProt round-trip needed for positives).

```bash
detectors/datasets/download_safeprotein.sh       # → detectors/datasets/safeprotein/
# emits SafeProtein_Bench.json, safeprotein.fasta, accessions.txt
```

**UniProt benigns + PDB cross-refs** — for the RFD3 partial-diffusion pipeline,
which needs full structures (not just sequences). Same exclusion filters as the
sequence-only benigns below, plus `database:PDB`. Downloads matching PDBs from
RCSB and emits a `sources.csv` ready for `tutorials/sae_data_rfd3_partial/`.

```bash
detectors/datasets/download_uniprot_pdb_benigns.sh                       # 200 default, length 100-400
detectors/datasets/download_uniprot_pdb_benigns.sh 500 80 600
```

**UniProt benigns — the universal sequence-only negative pool**. Cursor-paginated FASTA download
filtered by `reviewed:true NOT keyword:KW-0800 (Toxin) NOT keyword:KW-0843 (Virulence)
NOT taxonomy_id:10239 (Viruses)` and a length range. Matches SafeBench-Seq's recipe
(plus the stricter NOT virulence filter).

```bash
detectors/datasets/download_uniprot_benigns.sh                        # default 10000, length 1-2000
detectors/datasets/download_uniprot_benigns.sh 1500 50 600            # 1500 benigns, length 50-600
detectors/datasets/download_uniprot_benigns.sh 1500 50 600 /dest      # custom dest
```

Use any positive set as RFD3 scaffold inputs to generate labelled designs — the design's
label is inherited from its source file. Pair with `download_uniprot_benigns.sh` (or
ToxinPred's existing negatives) for the negative class.

SafeBench-Seq isn't publicly downloadable yet — see [`plan.md`](plan.md) for backup
plans (UniProt API, Victors, VFDB).

### Filtering + length-stratified balancing for partial diffusion

After downloading hazards + benigns into a single `sources.csv`, GPU memory and label-
shortcut concerns motivate trimming the dataset:

- **Drop oversized structures** — RCSB PDBs of binding-partner heterodimers or full
  cryo-EM complexes can balloon to thousands of residues. Cap at e.g. 300 residues
  to fit on a 44 GB GPU at `diffusion_batch_size=2`.
- **Length-stratify the class balance** — naïve filtering tends to leave length
  trivially separable between hazards and benigns. Per-bin balancing removes that
  shortcut.

```bash
# combine hazard + benign sources first
cat tutorials/sae_data_rfd3_partial/sources.csv \
    detectors/datasets/uniprot_pdb_benigns/sources.csv \
    > tutorials/sae_data_rfd3_partial/sources_combined.csv  # de-dupe headers manually

# filter ≤ 300 residues, length-stratify-balance per 50-residue bin
python tutorials/sae_data_rfd3_partial/balance_sources.py \
    --input  tutorials/sae_data_rfd3_partial/sources_combined.csv \
    --output tutorials/sae_data_rfd3_partial/sources.csv \
    --max-residues 300
```

Auto-counts residues if the input lacks an `n_residues` column (writes a sidecar
`<input>_counts.csv` for reuse). Output is a perfectly class-balanced CSV (177
hazards + 177 benigns at the standard 300-residue cap on the SafeProtein +
UniProt-benign datasets).

## Install

From the repo root:

```bash
uv pip install -e detectors/
```

Or add to the workspace and sync:

```bash
uv sync
```

## CLI

Every command takes exactly two flags: `inputs=<config.yaml|json>` and `out_dir=<path>`.
The config carries everything else (extractor, scorer, classifier, paths, hooks).

```bash
detect labels   inputs=detectors/src/detectors/configs/labels_safeprotein.yaml    out_dir=detectors/datasets/labels/safeprotein
detect score    inputs=detectors/src/detectors/configs/score_block8.yaml          out_dir=outputs/detect/score_block8
detect fit      inputs=detectors/src/detectors/configs/fit_block8_logistic.yaml   out_dir=outputs/detect/block8_lr
detect screen   inputs=detectors/src/detectors/configs/screen_block8.yaml         out_dir=outputs/detect/screen_block8
detect evaluate inputs=detectors/src/detectors/configs/screen_block8.yaml         out_dir=outputs/detect/eval_block8
```

`saffron screen` is an alias for `detect screen`.

## What each command does

| Command | Reads | Writes |
|---|---|---|
| `labels` | labelled FASTAs + activations.h5 | `labels.csv` (design_id → label) + `sources.csv` |
| `score` | activations.h5 + labels.csv | `feature_scores.parquet`, `feature_scores_top.md` — features ranked by AUROC vs the positive class |
| `fit` | activations.h5 + labels.csv | `bundle/` (extractor + detector + config), `metrics.json`, `train_predictions.csv` |
| `screen` | activations.h5 + bundle/ | `screen_report.csv` — per-design probability + prediction |
| `evaluate` | activations.h5 + bundle/ + labels.csv | `screen_report.csv` + `eval_metrics.json` (AUROC, accuracy) |

## Config shape

### `score`/`fit` config

```yaml
activations_path: /path/to/activations.h5
labels_path: /path/to/labels.csv         # columns: design_id,label
hook_name: block8                        # one of token_initializer_outputs, block8, block12, block16
extractor:
  kind: sae_encode                       # or 'identity' for raw activations
  checkpoint_path: /path/to/sae/final.pt
  device: cuda:0
pooling: last_step                       # max | mean | last_step | per_token
aggregation: mean                        # how to pool multiple samples per design

# fit-only
classifier: logistic                     # or 'top_feature'
classifier_kwargs:
  epochs: 300
  lr: 0.05
select_top_k: 50                         # optional: restrict to top-K AUROC features

# score-only
scorer: auroc
top_k: 50
```

### `screen`/`evaluate` config

```yaml
bundle_path: /path/to/bundle              # produced by `detect fit`
activations_path: /path/to/new_activations.h5
labels_path: /path/to/labels.csv          # evaluate only
```

### Labels CSV

```csv
design_id,label
design_001,1
design_002,0
```

Generated automatically by `detect labels` from labelled FASTAs:

```yaml
# labels_*.yaml
positives:                            # files whose entries get label=1
  - /path/to/safeprotein.fasta
  - /path/to/vfdb_setA_pro.fas
negatives:                            # files whose entries get label=0
  - /path/to/uniprot_benigns/benigns.fasta
activations_path: /path/to/activations.h5
```

The aligner extracts source IDs from FASTA headers (or `{stem}_{lineno}` for line-format
inputs like ToxinPred CSVs), then matches each `design_id` in the h5 to a source by
stripping the trailing `_<batch_index>` suffix that saffron-collect appends. Unmatched
design_ids are dropped (with a count printed). Convention: name your saffron-collect
input keys to match source IDs exactly.

## GPU

Not required. The only step that can use GPU is SAE encode, controlled by
`extractor.device` in the config (`cuda:0` or `cpu`). Everything else (h5 read, pooling,
scoring, logistic fit, screening) is CPU-only. The example configs default to `cuda:0`
for SAE encode — flip to `cpu` if you don't have a GPU available.

## Tests

```bash
cd detectors && uv run pytest
```

21 tests, ~15s. Covers AUROC edge cases (perfect/inverted/single-class), pooling
correctness, classifier save/load, end-to-end fit→screen on synthetic h5.

## Adding a new scorer

Add a `Scorer` entry in `src/detectors/scorers/__init__.py`:

```python
SCORERS["pearson"] = Scorer(pearson_vectorized, pearson_p_value, 0.0, "pearson_r", "pearson_p")
```

Then `scorer: pearson` in the `score` config.

## Adding a new classifier

Implement the `Detector` protocol (`fit`, `predict_proba`, `save`, `load`) in
`src/detectors/classifiers/<name>.py`, then register in
`src/detectors/classifiers/__init__.py`'s `DETECTORS` dict.
