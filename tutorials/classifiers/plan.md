# Classifier Sweep Plan — RF3 vs RFD3, raw vs SAE, hook sweep

## Goal

Use the SAEs trained at
- RF3 ToxinPred3: `outputs/sae/2026-04-26_15-23-45/train/{block12,block16,to_r_update,to_si}`
- RFD3 SafeProtein+UniProt: `outputs/sae/2026-04-26_15-38-55/train/{token_initializer_outputs,block6,block8,block12}`

to answer two research questions:
1. **Probing.** Which (model × hook × extractor) gives the best toxic/viral classifier?
2. **Attribution.** Which individual SAE features score highest for toxicity/virulence?

Constraint: only write code for functionality that doesn't already exist in `detectors/` or `sae/`.

---

## What already exists (reuse, don't rewrite)

`detectors/` already implements every primitive needed:

| Need | Existing piece |
|---|---|
| Build labels.csv from pos/neg FASTAs + h5 | `detect labels` |
| Univariate AUROC + Mann-Whitney p-values, top-K markdown | `detect score` |
| Fit logistic regression on raw or SAE features | `detect fit` (extractor: `identity` or `sae_encode`) |
| Held-out evaluation against a separate h5 | `detect evaluate` |
| Apply trained bundle to fresh designs | `detect screen` |
| Pooling: max / mean / last_step / per_token | `features/pooling.py` |
| Aggregation across multi-sample designs | `aggregation: mean/max/sum` |
| Per-feature top-firing tokens (residue attribution) | `sae/evaluation/feature_stats.top_firing_tokens` |
| Pre-pooled feature cache (.npz) | `pipelines/cache.py` |

⇒ Q1 and Q2 are largely a **configuration + orchestration** exercise, not a coding exercise.

---

## Answers to your implementation questions

### 1. Is it ok to encode the SAE-training activations with that same SAE to feed the probe?

Yes, with one caveat. SAE encoding is deterministic and the probe is a *separate* model — it doesn't matter that the SAE saw these activations. What matters is that the **probe** has a clean train/test split. Two acceptable patterns:

- **Hold out designs.** Split the design ids into 80/20 stratified by label and source. Train probe on 80%, evaluate on 20%. (Cheapest — no new activations needed.)
- **Hold out a separate activations.h5** collected on a different label set (this is what you've already done for RF3 with `test_activations/`).

Neither requires re-collecting the activations the SAE saw.

### 2. What's a good train/test split?

- **Stratify by label** (preserve toxic/benign ratio).
- **Stratify by source** (don't put all of SafeProtein in train, all of UniProt in test).
- **Group by sequence cluster** if you want to be strict — current data isn't huge so a clustered split (e.g. mmseqs2 at 30% identity) is the gold standard. Optional for v1.
- For RF3: `train_activations/` → train probe, `test_activations/` → eval. Already done.
- For RFD3 partial: you only have one h5. Easiest path is to split the labels CSV into `labels_train.csv` / `labels_test.csv` and let `detect fit` / `detect evaluate` read from the same h5 with different label files. The pipeline keys by design_id, so this works without re-running activation collection.

### 3. How do I label activations?

`detect labels` already does this. Inputs: positive FASTAs, negative FASTAs, the activations.h5. It matches FASTA headers to design_ids in the h5 and writes `labels.csv` (`design_id,label,source`).
- RF3 ToxinPred3: positives = `toxinpred3/train_pos.csv`, negatives = `toxinpred3/train_neg.csv` — *but the loader expects FASTA*; either convert these CSVs to FASTA or extend the existing label loader (small new function in `pipelines/labels.py`).
- RFD3 partial: positives = `safeprotein/safeprotein.fasta`, negatives = `uniprot_pdb_benigns/sources.csv` (need a tiny FASTA built from this CSV, or read the column directly).

### 4. Should I save SAE activations to disk?

The cache already does this: `build_feature_cache()` writes design-level pooled features to `.npz`. That's almost always what you want for probing — full per-token SAE activations would be ~8× larger and you don't need them once pooled. Keep the existing layout. **Only** materialize a per-token SAE h5 if you want to do per-residue attribution at scale (Q2 follow-up); for now, `feature_stats.top_firing_tokens` does that on the fly per-feature.

### Do you need to collect new activations to complete the cross product?

The natural cross-product is `{RF3, RFD3} × {ToxinPred3, SafeProtein/UniProt}` = 4 cells. Today you have 2 (the diagonal):

| | ToxinPred3 (peptides) | SafeProtein + UniProt (PDBs) |
|---|---|---|
| **RF3** (folding) | ✅ have | ❌ missing |
| **RFD3** (design / partial diffusion) | ❌ missing — needs predicted structures | ✅ have |

- **RF3 on SafeProtein/UniProt is cheap.** RF3 takes sequence; both datasets have FASTA. Run `saffron collect` with the same hooks.yaml as before but the new inputs JSON. *No new Python code.*
- **RFD3 on ToxinPred3 is more expensive.** RFD3 partial diffusion needs PDB structures. ToxinPred3 sequences are short peptides, no native structures — would need ESMFold/AlphaFold first. **Defer this cell.** It's the least informative anyway: RFD3 was designed for medium proteins.

⇒ After collecting the **RF3-on-SafeProtein/UniProt** cell, you can answer "RF3 vs RFD3" cleanly on a single label set.

---

## Research Q1 — Probing sweep

### Variables

- **Model:** `{rf3, rfd3}`
- **Hook:** RF3 = `{block12, block16, to_r_update, to_si}`; RFD3 = `{token_initializer_outputs, block6, block8, block12}`
- **Extractor:** `{identity, sae_encode}`
- **Label set:** start with SafeProtein/UniProt (apples-to-apples once you collect RF3 on it). ToxinPred3 stays a single-model RF3 result.

### Mechanics (existing CLI)

For each cell, one yaml + one `detect fit` + one `detect evaluate`. Mirror the pattern in `tutorials/sae_data_rf3/block12_logistic.yaml`. Vary `hook_name`, `extractor.kind` (identity vs sae_encode + checkpoint_path), and `activations_path`.

For each `(model, hook, extractor)` triple write:
```
tutorials/classifiers/configs/{label_set}/fit_{model}_{hook}_{extractor}.yaml
tutorials/classifiers/configs/{label_set}/eval_{model}_{hook}_{extractor}.yaml
```

Then a sweep shell script (one file, ~30 lines, mirrors `train_all_hooks.sh`):
```
tutorials/classifiers/sweep_probes.sh
```
that loops over the configs and writes each run's `metrics.json` under `outputs/detect/{label_set}/{model}/{hook}/{extractor}/`.

### Reporting

Tabulate AUROC across all cells. The metric is already in `metrics.json` per run; a small post-hoc script (`tutorials/classifiers/aggregate_metrics.py`, ~40 lines) globs them and produces a markdown table:
```
| model | hook | extractor | n_train | n_test | AUROC | AUPRC |
```

This script is the only meaningful **new Python** for Q1. Everything else is configs.

### Pooling choice

Default to `pooling: last_step` for dynamic hooks (matches what the SAE was trained on; matches `detectors/plan.md` decision) and `pooling: mean` over tokens. Sweeping pooling is a follow-up if the AUROC table is mediocre — don't blow up the search space upfront.

---

## Research Q2 — Top SAE features correlated with toxicity / virulence

### Mechanics (existing CLI)

`detect score` already does this end-to-end: AUROC per feature + Mann-Whitney U p-value for the top-K, sorted parquet, top-K markdown. Run once per `(model, hook)` cell with `extractor.kind: sae_encode`. **No new code for the per-feature scoring itself.**

```
tutorials/classifiers/configs/score_{model}_{hook}.yaml
tutorials/classifiers/sweep_scores.sh    # mirror sweep_probes.sh
```

### Multiple-testing correction (small gap)

You mentioned Benjamini-Hochberg. Yes, it's appropriate: with ~12k SAE features per hook, raw p-values overstate significance. BH-FDR is the right tool (Bonferroni would be too conservative for this many tests).

This is a **real gap** in `detectors/scorers/`. Two options:
- **Easiest:** post-hoc — read the `feature_scores.parquet`, apply `scipy.stats.false_discovery_control` (BH), write a column. Could be 10 lines in `aggregate_metrics.py` or a sibling script.
- **Better:** add a `bh_fdr` function in `detectors/src/detectors/scorers/pipeline.py` and emit a `q_value` column from `score_all_features`. ~15-line patch, fits the existing `Scorer` shape.

I'd recommend the in-package version since it makes the q-value a first-class output for everyone.

Mann-Whitney U is what's already used (it *is* the AUROC null distribution), so don't add it as a separate scorer.

### Cross-hook stability

If a feature has high AUROC at multiple hooks for the same label, that's a stronger signal than one hook alone. Optional: a small notebook joining the per-hook parquets on `feature_id` (after mapping — feature ids aren't comparable across hooks since each SAE is trained independently, so this is a *count of "high-AUROC hooks per dataset"* analysis, not feature-id-level). Defer unless Q2 results are noisy.

---

## Concrete next steps (ordered)

### Step 0 — Decide the label-set strategy
- ToxinPred3 (RF3-only, you already have it): straight-line sweep over RF3 hooks.
- SafeProtein/UniProt: collect RF3 activations on this set so you can compare RF3 vs RFD3.

### Step 1 — Collect RF3 activations on SafeProtein/UniProt **(no new Python, just config)**
- Reuse `tutorials/sae_data_rfd3_partial/sources.csv` for the FASTA list.
- Build a `tutorials/classifiers/rf3_safeprotein/inputs.json` (mirror `tutorials/sae_data_rf3/build_inputs.py` — that script reads pos/neg sources and emits the saffron inputs JSON). One small reuse + path edit.
- Run `saffron collect model=rf3 inputs=... out_dir=tutorials/classifiers/rf3_safeprotein/activations` with the same `hooks.yaml` used for SAE training.

### Step 2 — Build labels for both label sets **(reuse `detect labels`)**
- `tutorials/classifiers/configs/labels_toxinpred3.yaml` — already covered by `tutorials/sae_data_rf3/label_acts.yaml`, just point at train + test activations.
- `tutorials/classifiers/configs/labels_safeprotein.yaml` — point positives at `safeprotein/safeprotein.fasta`, negatives at the UniProt benigns FASTA, activations at the new RF3 collection (Step 1) **and** the existing RFD3 collection (one labels file per activations.h5).
- ⚠️ **Small new code if needed:** if `detect labels` only accepts FASTA and you have CSVs (ToxinPred3), add a CSV-aware branch in `detectors/src/detectors/pipelines/labels.py`. Keep it minimal — one helper that reads a CSV with `sequence`/`id` columns into the same internal representation as the FASTA loader.

### Step 3 — Make a stratified train/test split for RFD3 **(no new code)**
- 80/20 stratified by `(label, source)` over the design_ids in `labels.csv`. ~10-line numpy script that writes `labels_train.csv` and `labels_test.csv` (or just sklearn `train_test_split`). Put it in `tutorials/classifiers/split_labels.py`.

### Step 4 — Write the sweep configs **(configs only)**
For each `(model, hook, extractor)` produce a fit yaml and an eval yaml. Suggest a tiny generator script (`generate_configs.py`, ~50 lines) so adding a hook is one entry, not 4 yaml edits.

### Step 5 — Run sweeps **(shell only)**
- `sweep_probes.sh` — loops over configs, calls `detect fit` then `detect evaluate`.
- `sweep_scores.sh` — loops over configs, calls `detect score`.

### Step 6 — Aggregate results **(small new Python)**
- `aggregate_metrics.py` — globs `outputs/detect/**/metrics.json`, emits a markdown table grouped by label set.
- For Q2, add BH-FDR (in-package preferred — see "Multiple-testing correction" above) and a `top_features_report.py` that joins per-hook top-K parquets with structure-level metadata (PDB id, source) for human inspection.

### Step 7 — Per-residue follow-up (optional)
Only if Q2 yields a few dramatic features. Use `sae/evaluation/feature_stats.top_firing_tokens` + the existing PyMOL viz to render where each top feature fires on a hazardous structure. No new code beyond a small notebook.

---

## Summary of new code recommended

| File | Size | Purpose |
|---|---|---|
| `detectors/src/detectors/scorers/pipeline.py` (patch) | +~15 lines | Add BH-FDR `q_value` column |
| `detectors/src/detectors/pipelines/labels.py` (patch, *if needed*) | +~20 lines | CSV label loader (skip if you convert ToxinPred3 to FASTA) |
| `tutorials/classifiers/build_inputs_rf3_safeprotein.py` | ~40 lines | Wraps existing `build_inputs.py` for the new dataset |
| `tutorials/classifiers/split_labels.py` | ~30 lines | Stratified train/test split for RFD3 |
| `tutorials/classifiers/generate_configs.py` | ~50 lines | Templated yaml emitter for the sweep |
| `tutorials/classifiers/sweep_probes.sh`, `sweep_scores.sh` | ~30 lines each | Run the sweep |
| `tutorials/classifiers/aggregate_metrics.py` | ~60 lines | Markdown comparison table from `metrics.json` files + BH q-values |

Everything else — feature extraction, SAE encoding, AUROC, Mann-Whitney, logistic regression, train/eval, bundle save/load, top-firing-tokens — is already in `detectors/` and `sae/`. **No changes to `sae/` are required.**

---

## Quick gotchas

- **Feature ids are not comparable across hooks** (each SAE trained independently). Don't try to join Q2 parquets on `feature_id` across hooks.
- **`select_top_k` in `detect fit`** uses an internal AUROC score on the *training* split for feature selection. That's fine but document it — it's not test-set leakage but it does inflate "effective" capacity. Reporting both with and without `select_top_k` is informative.
- **Last-step alignment**: the dynamic hooks (`block*`) collect every-50th step. Make sure the `last_step` pooling key in `detectors/features/pooling.py` actually picks the final collected step, not step 0. (Worth a quick check on a single design before sweeping.)
- **Class imbalance.** If SafeProtein/UniProt is unbalanced after length filtering, AUROC is robust but report AUPRC alongside. `detect evaluate` should already emit it; if not, that's a tiny addition.
- **RFD3 length cap (<300 residues)** carries through to the probe — don't compare cross-model AUROCs on different length distributions.
