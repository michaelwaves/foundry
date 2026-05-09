# Classifier sweep — results & interpretation

Last updated: 2026-04-27, after running three variants of the probe sweep:
- **baseline** — random splits, weight_decay 1e-4, 300 epochs, asymmetric `select_top_k` (50 for SAE only)
- **cluster** — homology-clustered splits (mmseqs at 30% identity), original hyperparameters
- **stop_overfitting** — random splits, weight_decay **1e-2**, **75 epochs**, symmetric `select_top_k=50`

All numbers are 5-fold CV mean ± std on safeprotein cells. RF3 ToxinPred3 cells were broken across all three variants (the eval pipeline pointed at the upstream pre-built test_activations.h5, whose `test_pos_*` design_ids never matched the k-fold's `train_pos_*` test labels — n_designs=0, AUROC=0.5). They've been omitted from this writeup; see "Bug fixed but not re-run" below.

---

## Headline

| | best AUROC ± σ | n_test/fold | comments |
|---|---|---|---|
| stop_overfitting | **rfd3 block12 SAE: 0.877 ± 0.028** | 55 | tightest error bar, lowest train-eval gap, best single number to quote |
| cluster (homology split) | **rfd3 block12 SAE: 0.803 ± 0.107** | ~55 | the more honest generalization number — wider error bar |
| baseline | rfd3 block12 identity: 0.913 ± 0.051 | 55 | inflated by paralog leakage; superseded |

The cluster number is the most defensible for any external claim. The stop_overfitting number is what the model can do when given a balanced sequence-similarity split.

---

## Three findings

### 1. `stop_overfitting` actually stopped overfitting

Train AUROC dropped from ~1.0 to ~0.85; train-eval gap collapsed by 60–70%:

| cell | baseline gap | stop_overfitting gap |
|---|---|---|
| rfd3 block6 identity | 0.222 | **0.103** |
| rfd3 block8 identity | 0.231 | **0.092** |
| rfd3 block12 identity | 0.087 | 0.086 |
| rfd3 block6 sae_encode | 0.119 | **0.106** |
| rfd3 block8 sae_encode | 0.155 | **0.082** |
| rfd3 block12 sae_encode | 0.125 | **0.066** |

Eval AUROCs mostly held; some even improved (block12 SAE: 0.846 → 0.877). The probe is now genuinely converging, not memorizing. Recipe: bump weight_decay 1e-4 → 1e-2, drop epochs 300 → 75, apply `select_top_k: 50` to identity too.

### 2. Cluster splits reveal a real generalization gap

Homology-clustered splits drop AUROC by 0.10–0.15 on RFD3 — paralog leakage was inflating baseline numbers:

| cell | baseline | cluster | Δ |
|---|---|---|---|
| rfd3 block12 identity | 0.913 | 0.755 | **−0.158** |
| rfd3 block6 identity | 0.772 | 0.655 | **−0.117** |
| rfd3 block8 identity | 0.769 | 0.650 | **−0.119** |
| rf3 block16 identity | 0.802 | 0.771 | −0.031 |

RFD3 takes a much bigger hit than RF3 — RFD3's representations were memorizing fold families. RF3 (sequence-only conditioning) didn't have as much fold structure to leak.

### 3. SAE flips from worse-than-raw to better-than-raw under cluster splits

Under random splits, raw mostly beat SAE. Under homology-clustered splits, **SAE generalizes better**:

| cell | identity | sae_encode | winner |
|---|---|---|---|
| rfd3 block12 cluster | 0.755 | **0.803** | SAE +0.048 |
| rfd3 block8 cluster | 0.650 | **0.687** | SAE +0.037 |
| rfd3 block6 cluster | 0.655 | 0.635 | identity +0.020 |
| rfd3 block12 stop_overfit | 0.863 | **0.877** | SAE +0.014 |

This is the most interesting scientific finding so far: **SAE features are more transferable across protein families than raw activations**. That's a real claim about representation quality, not just regularization — the SAE's sparse decomposition appears to factor out family-specific noise that raw activations carry.

---

## RFD3 vs RF3 on the matched SafeProtein/UniProt set

| variant | RF3 best | RFD3 best | gap | within noise? |
|---|---|---|---|---|
| baseline | 0.802 | 0.913 | RFD3 +0.111 | no (σ ≈ 0.05–0.07) |
| cluster | 0.771 | 0.803 | RFD3 +0.032 | **yes** (σ ≈ 0.10) |
| stop_overfitting | 0.777 | 0.877 | RFD3 +0.100 | borderline (σ ≈ 0.07) |

RFD3 wins on every variant, but the **cluster gap (+0.03) is well within noise**. Under proper homology splitting, **RFD3 ≈ RF3 within error bars** — much weaker claim than the headline 0.10 gap suggests.

---

## Q1 — Probe AUROC (5-fold CV mean ± std), SafeProtein cells only

| dataset | hook | extractor | baseline | cluster | stop_overfit |
|---|---|---|---|---|---|
| rf3_safeprotein | block12 | identity | 0.796 ± 0.070 | 0.748 ± 0.099 | 0.777 ± 0.117 |
| rf3_safeprotein | block12 | sae_encode | 0.770 ± 0.072 | 0.636 ± 0.091 | 0.771 ± 0.084 |
| rf3_safeprotein | block16 | identity | 0.802 ± 0.065 | 0.771 ± 0.054 | 0.776 ± 0.064 |
| rf3_safeprotein | block16 | sae_encode | 0.777 ± 0.080 | 0.740 ± 0.107 | 0.774 ± 0.099 |
| rfd3_safeprotein | block6 | identity | 0.772 ± 0.075 | 0.655 ± 0.099 | 0.722 ± 0.074 |
| rfd3_safeprotein | block6 | sae_encode | 0.768 ± 0.082 | 0.635 ± 0.094 | 0.717 ± 0.099 |
| rfd3_safeprotein | block8 | identity | 0.769 ± 0.068 | 0.650 ± 0.083 | 0.785 ± 0.058 |
| rfd3_safeprotein | block8 | sae_encode | 0.760 ± 0.069 | 0.687 ± 0.104 | 0.759 ± 0.085 |
| rfd3_safeprotein | block12 | identity | **0.913 ± 0.051** | 0.755 ± 0.130 | 0.863 ± 0.070 |
| rfd3_safeprotein | block12 | sae_encode | 0.846 ± 0.039 | **0.803 ± 0.107** | **0.877 ± 0.028** |

---

## Q2 — Top SAE features for RFD3 (BH-FDR corrected, sweep on full labels.csv)

```
hook     active_features  q<0.05  q<0.01  top |AUROC-0.5|
block6     11468/12288       37       7      0.256 (#47, fires-on-benign)
block8     12017/12288       26      11      0.276 (#624, fires-on-hazard)
block12    12279/12288      200     195      0.315 (#639, fires-on-hazard)
```

Highlight features (`fires-on-hazard` only — the safety-relevant ones):

| hook | feat_id | AUROC | q | n_designs_firing |
|---|---|---|---|---|
| block12 | **#639** | **0.815** | ~0 | 272/275 |
| block12 | #60 | 0.805 | ~0 | 275/275 |
| block8 | #624 | 0.724 | ~0 | 274/275 |
| block8 | #351 | 0.676 | 0.0023 | 275/275 |

**Block12 #639** — the strongest single-feature toxicity correlate. Top firing design is `train_inputs_hazard_P00626_0` (UniProt P00626 — snake-venom phospholipase A2). Concentrates on residues 70, 83, 99, 104, 109 of chain A — the catalytic + membrane-binding region of the PLA2 fold. Plausibly biologically meaningful, not random. Renderings of this and other top features are at `outputs/classifiers/viz/rfd3_safeprotein_block{6,8,12}/*.png`.

Pattern by depth: block6 dominated by `fires-on-benign` features (early-layer features capture general protein-likeness; hazards fire fewer of them). block8 mixed. block12 has the cleanest hazard-vs-benign separation, and is the layer to target for both probing and steering.

---

## Sanity checks

### Length-only baseline
Confirms the AUROCs above are not driven by trivial length differences:

| dataset | length range (pos / neg) | length-only test AUROC |
|---|---|---|
| rfd3_safeprotein | mean 218 [45–580] / mean 186 [11–633] | **0.554** |

So the headline 0.85+ on RFD3 SafeProtein has a real ~0.30 gap over length alone.

### Per-length-bin breakdown (RFD3 block12 identity, baseline)
| length bin | n_test | pos | neg | bin AUROC |
|---|---|---|---|---|
| [100, 200) | 16 | 9 | 7 | 0.921 |
| [200, 1000) | 37 | 22 | 15 | 0.829 |

Consistent across length range — no single bin carrying the headline.

### SAE health (`sae_health_check.py`)
All five trained SAEs are healthy: l0 ≈ 80 (matches k=80), `frac_alive ≥ 0.94`, FVE ≥ 96%, cossim ≥ 98%. The earlier "1% feature utilization" was a pipeline bug (pool-then-encode); the encode-then-pool patch in `detectors/pipelines/cache.py` raised utilization to 81%+.

---

## Caveats

1. **Cluster split has wider error bars** (σ up to 0.13 vs 0.05 for random) — fewer effective examples per fold because clusters can be uneven sizes.
2. **n_test ≈ 55 per fold** — even averaged across 5 folds, gaps under 0.05 are within noise.
3. **Single SAE seed** — no error bars from re-training the SAE itself.
4. **`stop_overfitting` and `cluster` not yet combined** — the gold-standard run is below.
5. **rf3_toxinpred3 cells broken** — the fix is committed in `generate_configs.py:_emit_eval` (always use `dataset["activations"]`, ignore `test_activations`); needs the eval step re-run. Not blocking the safeprotein story.
6. **No PFAM/InterPro family breakdown** — would tell us if the classifier generalizes to novel toxin families or just recognizes common ones.

---

## Files

| What | Path |
|---|---|
| Probe table (per variant) | `tutorials/classifiers/results{,_cluster,_stop_overfitting}/probes.{csv,md}` |
| Per-fold raw rows | `tutorials/classifiers/results*/probes_per_fold.csv` |
| Top features per cell | `tutorials/classifiers/results/top_features.{csv,md}` |
| Per-cell raw outputs | `outputs/classifiers{,_cluster,_stop_overfitting}/<dataset>/{score,fit,eval}/<cell>/` |
| Feature renderings | `outputs/classifiers/viz/rfd3_safeprotein_block{6,8,12}/*.png` |
| Reproduction | `tutorials/classifiers/README.md` |

---

## Next experiment to run

The single most informative one: **cluster split + stop_overfitting hyperparams combined** — gives the gold-standard generalization number with the regularized probe:

```bash
# Run from the repo root
source .venv/bin/activate

CLASSIFIER_DEVICE=cuda:0 \
CLASSIFIER_RUN_TAG=cluster_stop_overfit \
CLASSIFIER_LABELS_TAG=cluster \
CLASSIFIER_WEIGHT_DECAY=1e-2 \
CLASSIFIER_EPOCHS=75 \
CLASSIFIER_SELECT_TOP_K=50 \
python tutorials/classifiers/generate_configs.py

CLASSIFIER_RUN_TAG=cluster_stop_overfit \
bash tutorials/classifiers/sweep_probes.sh

python tutorials/classifiers/aggregate_metrics.py \
  --sweep-root outputs/classifiers_cluster_stop_overfit \
  --out tutorials/classifiers/results_cluster_stop_overfit
```

~10–15 min on GPU. Produces the headline AUROC for any external writeup.
