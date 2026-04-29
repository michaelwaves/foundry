# Detector Plan

Goal: classify RFD3 designs (or per-token activations) as toxic/viral vs benign using the
trained Matryoshka BatchTopK SAEs at `outputs/sae/2026-04-20_05-38-45/train/{hook}/final.pt`,
and rank which **individual features** correlate with the positive class. Leave room for
non-SAE classifiers (logistic regression on raw activations, etc.).

## Architecture decision

Sibling package `detectors/` that **depends on `sae/`** but does not modify it.
Add one new subcommand `saffron screen` (in `sae/cli.py`) that delegates into `detectors`
so users have one CLI surface, while detector code lives separately and can be iterated on
without touching SAE training.

**Why not embed in saffron:** `saffron collect/train/eval` are about *making and inspecting*
features. Detectors are about *using* features for downstream classification + per-feature
hypothesis testing. Different lifecycle, different deps (sklearn, scipy.stats), and we may
want to reuse outside saffron later.

**Why not fully standalone:** loading SAEs, iterating designs, and reading the h5 activation
format is exactly what `sae/dataset.py` and `sae/evaluation/activations.py` already do.
Reuse, don't duplicate.

## Three orthogonal axes

The pipeline cleanly factors into three independent components:

| Axis | Purpose | Examples |
|---|---|---|
| **FeatureExtractor** | (N, D_act) → (N, D_feat) | `SAEEncodeExtractor`, `IdentityExtractor` |
| **Scorer** | rank features by class correlation | `auroc` (default), `spearman`, `lift` |
| **Detector** | features → label/probability | `LogisticDetector`, `MLPDetector`, `TopFeatureThreshold` |

You can mix and match: SAE features + AUROC ranking → top-50 features → logistic regression.
Or raw activations + AUROC ranking → top-k channels → linear probe. Or skip the detector
entirely and ship the feature ranking as the deliverable.

## Directory layout

```
detectors/
  plan.md
  data_pipelines/
    lit_review.csv
    labels/                    # per-source label CSVs (design_id -> label)
  src/detectors/
    __init__.py
    cli.py                     # typer app: label, score, fit, screen, eval
    configs/                   # hydra configs (label.yaml, score.yaml, fit.yaml, screen.yaml, eval.yaml)
    features/
      base.py                  # FeatureExtractor protocol
      sae_encode.py            # wraps MatryoshkaBatchTopKSAE.encode
      identity.py              # raw activations passthrough
      pooling.py               # design-level aggregations (mean, max, topk-mean, last-step)
    scorers/
      base.py                  # Scorer dataclass (score_all, compute_p_value, null_value)
      auroc.py                 # vectorized AUROC + Mann-Whitney U p-value (default)
      spearman.py              # rank correlation (for continuous targets — later)
      lift.py                  # mean-when-fires - mean-target (rare-but-discriminative — later)
      pipeline.py              # score_all_features(matrix, target, scorer) -> DataFrame
    classifiers/
      base.py                  # Detector protocol (fit/predict_proba/save/load)
      logistic.py              # sklearn LR
      top_feature.py           # threshold the highest-AUROC single feature (baseline)
      mlp.py                   # small torch MLP (later)
    pipelines/
      labeled_dataset.py       # join activations + labels -> (X, y, design_id)
      score.py                 # extract features, run scorer, write feature_scores.parquet
      fit.py                   # extract features, fit detector, save artifact
      screen.py                # load detector, score new activations, emit report
    io/
      artifacts.py             # save/load Detector + FeatureExtractor bundle
```

One class per file. Functions ordered high-level first, per global guidelines.

## Core interfaces

```python
# features/base.py
class FeatureExtractor(Protocol):
    feature_dim: int
    def transform(self, activations: Tensor) -> Tensor: ...   # (N, D_act) -> (N, D_feat)
    def save(self, dir: Path) -> None: ...
    @classmethod
    def load(cls, dir: Path) -> "FeatureExtractor": ...

# scorers/base.py — direct port of ~/repos/sae_experiments/scorers.py
@dataclass
class Scorer:
    score_all: Callable[[ndarray, ndarray], ndarray]   # (N, F) x (N,) -> (F,)
    compute_p_value: Callable[[ndarray, ndarray], float]
    null_value: float                                   # e.g. 0.5 for AUROC, 0.0 for spearman
    score_column: str
    p_value_column: str

SCORERS = {"auroc": ..., "spearman": ..., "lift": ...}

# classifiers/base.py
class Detector(Protocol):
    def fit(self, features: ndarray, labels: ndarray) -> None: ...
    def predict_proba(self, features: ndarray) -> ndarray: ...
    def save(self, dir: Path) -> None: ...
    @classmethod
    def load(cls, dir: Path) -> "Detector": ...
```

Initial implementations: `SAEEncodeExtractor` + `IdentityExtractor`; `auroc` scorer;
`LogisticDetector` + `TopFeatureThresholdDetector` (single-feature threshold from top-AUROC,
sanity baseline that pressure-tests whether anything beyond "one SAE feature" is needed).

## Scoring pipeline (mirrors sae_experiments/score_features.py)

For each feature `f` in the extracted feature matrix:
1. Aggregate per-design (max / mean / sum across tokens × steps) → (N_designs, F).
2. Vectorized score: `scorer.score_all(matrix, target) -> (F,)`.
3. P-values only for top-K features by |score - null| (full sweep wasteful at F=16k).
4. Constant-feature mask → set null score, p=1.
5. Output: parquet of `(feature_id, score, p_value, n_samples)` sorted by |score - null|.

Reusing the AUROC trick from sae_experiments: rankdata once, compute Mann-Whitney U
closed-form across all features in one pass — fast enough for full SAE dictionaries.

## Data flow

1. **Label** — given a hazard list (e.g. SafeBench-Seq UniProt accessions), produce a
   per-design CSV `design_id,label,source`. Lives in `data_pipelines/labels/`.
2. **Score** *(optional, but the interpretability deliverable)* — extract features, run
   scorer against labels, write `feature_scores.parquet` + a top-K markdown report.
   Independent of fit; can run on its own.
3. **Fit** — load activations via `iter_design_activations`, pool to design-level, apply
   `FeatureExtractor`, optionally restrict to top-K features from a prior `score` run,
   train `Detector`. Save a bundle: `{out_dir}/{detector.pkl, extractor/, config.yaml,
   metrics.json, feature_scores.parquet}`.
4. **Screen** — given a fresh `activations.h5` from `saffron collect`, load the bundle,
   produce `{design_id, score, top_features}` per design.
5. **Eval** — run a held-out split through screen + report AUROC, AUPRC, calibration.

Pooling: per-token classification gives interpretability ("which residue is toxic-like?"),
design-level pooling gives a single screening verdict. Support both via a `PoolingStrategy`
enum (`MAX`, `MEAN`, `TOPK_MEAN`, `LAST_STEP`, `PER_TOKEN`).

## CLI

Every command takes exactly two flags: `inputs=<config>` and `out_dir=<path>`. The config
file (yaml/json) carries everything else — extractor choice, scorer, classifier, activation
path, label path, hook name, pooling strategy. Mirrors the `saffron` `inputs=<file>` pattern.

```
detect label   inputs=detectors/configs/label_safebench.yaml   out_dir=...
detect score   inputs=detectors/configs/score_block8.yaml      out_dir=...
detect fit     inputs=detectors/configs/fit_block8_lr.yaml     out_dir=...
detect screen  inputs=detectors/configs/screen_safebench.yaml  out_dir=...
detect eval    inputs=detectors/configs/eval_safebench.yaml    out_dir=...
```

Implementation: typer + hydra-compose. The CLI body is a thin shim — read `inputs`, set
`out_dir`, call the pipeline function. Add `saffron screen` as an alias importing
`detect screen`. (Single-command-with-mode-flag was considered but kept separate for
consistency with the rest of the foundry CLI surface, e.g. RFD3 design passthrough.)

## Phasing

1. Wire the bundle layout + a no-op `IdentityExtractor` + `LogisticDetector` end-to-end
   on a tiny synthetic split. Pins the interfaces.
2. Port `Scorer` + `auroc` from sae_experiments. Add `detect score` CLI. Shippable on
   its own as "which SAE features fire on toxic designs?"
3. Add `SAEEncodeExtractor` over the four trained hooks; compare LR-on-SAE vs LR-on-raw,
   plus `TopFeatureThresholdDetector` baseline.
4. Add ToxinPred2 / SafeBench-Seq label loaders under `data_pipelines/labels/`.
5. Per-token reporting (which features fire on hazardous residues) — reuse
   `feature_stats.top_firing_tokens` from `sae/evaluation` plus the existing PyMOL viz.
6. Optional: spearman / lift scorers, MLP head, multi-hook fusion if marginal.

## Decisions

- **Per-hook detectors first**, no fusion. Add concat / ensemble across
  `{token_initializer, block8, block12, block16}` only if a single hook is clearly
  insufficient.
- **Dynamic hooks (`block8/12/16`) → use the last denoising step**. The structures and
  PDBs saved by `saffron collect` correspond to the last step, so per-token activations
  line up with atoms for downstream PyMOL highlighting. Other steps left as future work.
- **Default scorer: AUROC** (binary toxic/benign). Spearman if we get a continuous
  toxicity score (LD50, MIC); Lift to surface rare-but-discriminative features.

## Feature cache

Pre-compute pooled features once and write to parquet. `score` and `fit` both read from
this cache — the SAE encode pass is the expensive step and we don't want to repeat it.

```
{out_dir}/features.parquet   # (design_id, sample, step, token, feature_id, value)
                             # or pre-pooled: (design_id, feature_id, value) when
                             # PoolingStrategy != PER_TOKEN
```

DuckDB can aggregate (max/mean/sum across tokens × steps) directly out of this parquet,
matching the sae_experiments `score_features.py` pattern. `screen` keeps lazy-h5
streaming since it's a one-shot pass on novel designs and the parquet adds latency.

Add a `detect cache` (or implicit step inside `score`/`fit`) that materialises this once
per `(activations.h5, hook, extractor)` triple.

## Score vs Fit (clarification)

| | `score` | `fit` |
|---|---|---|
| What | Per-feature univariate ranking | Multivariate classifier |
| Output | Sorted parquet `(feature_id, auroc, p)` | Trained model + bundle |
| Answers | "Which features fire on positives?" | "Is this new design toxic?" |
| Train/test split | Not strictly needed | Required |
| Composition | Feeds `fit` via `select_top_k=N` | Can run alone, or after `score` |

Both consume the cached `(N_designs, F_features)` matrix.
