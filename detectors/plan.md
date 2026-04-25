# Detector Plan

Goal: classify RFD3 designs (or per-token activations) as toxic/viral vs benign using the
trained Matryoshka BatchTopK SAEs at `outputs/sae/2026-04-20_05-38-45/train/{hook}/final.pt`,
and leave room for non-SAE classifiers (logistic regression on raw activations, etc.).

## Architecture decision

Sibling package `detectors/` that **depends on `sae/`** but does not modify it.
Add one new subcommand `saffron screen` (in `sae/cli.py`) that delegates into `detectors`
so users have one CLI surface, while detector code lives separately and can be iterated on
without touching SAE training.

**Why not embed in saffron:** `saffron collect/train/eval` are about *making and inspecting*
features. Detectors are about *using* features for downstream classification. Different
lifecycle, different deps (sklearn), and we may want to reuse outside saffron later.

**Why not fully standalone:** loading SAEs, iterating designs, and reading the h5 activation
format is exactly what `sae/dataset.py` and `sae/evaluation/activations.py` already do.
Reuse, don't duplicate.

## Directory layout

```
detectors/
  plan.md
  datasets/
    lit_review.csv
    labels/                    # per-source label CSVs (design_id -> label)
  src/detectors/
    __init__.py
    cli.py                     # typer app: label, fit, screen, eval
    configs/                   # hydra configs (fit.yaml, screen.yaml)
    features/
      base.py                  # FeatureExtractor protocol
      sae_encode.py            # wraps MatryoshkaBatchTopKSAE.encode
      identity.py              # raw activations passthrough
      pooling.py               # design-level aggregations (mean, max, topk-mean)
    classifiers/
      base.py                  # Detector protocol (fit/predict_proba/save/load)
      logistic.py              # sklearn LR
      mlp.py                   # small torch MLP (later)
    C: scorers/                    
      auroc/
    pipelines/
      labeled_dataset.py       # join activations + labels -> (X, y, design_id)
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

# classifiers/base.py
class Detector(Protocol):
    def fit(self, features: ndarray, labels: ndarray) -> None: ...
    def predict_proba(self, features: ndarray) -> ndarray: ...
    def save(self, dir: Path) -> None: ...
    @classmethod
    def load(cls, dir: Path) -> "Detector": ...
```

Two backends initially: `SAEEncodeExtractor(checkpoint_path)` and `IdentityExtractor()`.
Two classifiers initially: `LogisticDetector` and `TopKMeanThresholdDetector` (toy baseline).

## Data flow

1. **Label** — given a hazard list (e.g. SafeBench-Seq UniProt accessions), produce a
   per-design CSV `design_id,label,source`. Lives in `detectors/datasets/labels/`.
2. **Fit** — load activations via `iter_design_activations`, pool to design-level features
   (or keep per-token), apply `FeatureExtractor`, train `Detector`. Save a bundle:
   `{out_dir}/{detector.pkl, extractor/, config.yaml, metrics.json}`.
3. **Screen** — given a fresh `activations.h5` from `saffron collect`, load the bundle,
   produce `{design_id, score, top_features}` per design.

Pooling matters: per-token classification gives interpretability ("which residue is toxic-like?"),
design-level pooling gives a single screening verdict. Support both via a `PoolingStrategy` enum.

## CLI

```
detect label   inputs=detectors/datasets/labels/safebench.yaml
detect fit     features=sae_encode classifier=logistic hook=block8 \
               activations=... labels=... out_dir=...
detect screen  bundle=outputs/detect/.../bundle activations=...  out=report.json
detect eval    bundle=... labels=... split=test
```
C: i want to have it possible for each command to have just 2 cli flags: inputs=path/to/confg and out_dir=/path to outputs. Ideally just one command (input config yaml or json) but i know there are some issues with not having outputs for rfd3 design passthru, so we keep it just to be consistent. 

Mirror `saffron`: typer + hydra-compose, `inputs=<file>` override pattern from `cli.py`.
Add `saffron screen` as a thin alias that imports and runs `detect screen`.

## Phasing

1. Wire the bundle layout + a no-op `IdentityExtractor` + `LogisticDetector` end-to-end
   on a tiny synthetic split. This pins the interfaces.
2. Add `SAEEncodeExtractor` over the four trained hooks; compare LR-on-SAE vs LR-on-raw.
3. Add ToxinPred2 / SafeBench-Seq label loaders under `datasets/labels/`.
4. Add per-token reporting (which features fire on hazardous residues) — reuse
   `feature_stats.top_firing_tokens` from `sae/evaluation`.
5. Optional MLP / non-linear heads if linear underperforms.

## Open questions

- Where to materialise per-design activations for fit/screen? Keep h5 + lazy-iterate (cheaper)
  or pre-compute pooled features to a parquet (faster iteration). Default to lazy.
- Multi-hook fusion: concatenate features across `{token_initializer, block8, block12, block16}`
  or fit per-hook detectors and ensemble. Start per-hook; add fusion if marginal.
  C: i think start per hook, add fusion later
- How to handle the dynamic hooks (`block8/12/16`) which fire many times per design — pool
  across denoising steps, or pick a single canonical step (e.g. middle of trajectory)?
  C: pick the last step for now (because the atom structures and pdbs saved by saffron collect are these, so easy to do viz later, render the highlighted activations).