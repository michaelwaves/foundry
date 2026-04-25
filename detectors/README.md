# detectors

Toxic/viral classifiers over RFD3 SAE features. Three orthogonal axes:
**FeatureExtractor** (raw or SAE-encoded) × **Scorer** (AUROC) × **Detector** (logistic / top-feature threshold).

See [`plan.md`](plan.md) for the full design. Lit review of toxic/viral datasets in
[`datasets/lit_review.csv`](datasets/lit_review.csv).

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
detect score    inputs=detectors/src/detectors/configs/score_block8.yaml      out_dir=outputs/detect/score_block8
detect fit      inputs=detectors/src/detectors/configs/fit_block8_logistic.yaml  out_dir=outputs/detect/block8_lr
detect screen   inputs=detectors/src/detectors/configs/screen_block8.yaml     out_dir=outputs/detect/screen_block8
detect evaluate inputs=detectors/src/detectors/configs/screen_block8.yaml     out_dir=outputs/detect/eval_block8
```

`saffron screen` is an alias for `detect screen`.

## What each command does

| Command | Reads | Writes |
|---|---|---|
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
