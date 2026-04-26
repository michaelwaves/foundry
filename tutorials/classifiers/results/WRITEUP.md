
  - Raw beats SAE in every cell. The 12k-feature SAE only fires on
  ~100–330 features, so its effective dimensionality is lower than the
  768-d raw, not higher.
  - Deeper hooks > shallower for RFD3: 0.67 → 0.78 → 0.85 from block6 →
  block8 → block12. Same trend (smaller) for RF3.
  - Heavy overfitting on RFD3 (220 train designs vs 768 raw dims → train
  AUROC ~1.0, eval ~0.85). Ratio is uglier for SAE (12k features).
  - ⚠️  Cross-model comparison is on different label sets right now
  (SafeProtein/UniProt vs ToxinPred3). The matched RF3-on-SafeProtein cell
   needs the RF3 SAE training you've got running. Once it lands, regen
  configs and re-sweep — the harness handles it.

  Q2 — Top SAE features per RFD3 hook (BH-corrected, priority result)

  - block12 #123 — AUROC 0.717, q ≈ 0, fires on 260/275 designs. Strongest
   hazard-firing feature found.
  - block8 #307 — AUROC 0.666, q = 0.0001, fires on 233/275.
  Second-strongest hazard-firing.
  - block6 has only benign-firing features in its top 10 — early-layer
  features capturing common protein patterns that hazards lack.
  - Significance density rises with depth: block6 has 10 features at
  q<0.05, block8 has 19, block12 has 31.

  Files

  - tutorials/classifiers/results/probes.{csv,md} — full Q1 table
  - tutorials/classifiers/results/top_features.{csv,md} — top-20 features
  per (dataset, hook, extractor)
  - Per-cell raw outputs under
  outputs/classifiers/<dataset>/{score,fit,eval}/<cell>/

  Caveats worth flagging in any writeup

  1. Sparse SAE utilization (~1–3% of features fire) suggests the SAEs may
   be undertrained or k=80 is too aggressive at this scale.
  2. No homology clustering in the train/test split — paralog leakage may
  inflate AUROCs.
  3. Single seed for both SAEs and probes; no error bars.
  4. token_initializer_outputs and to_si hooks skipped — they're
  3D-per-step in the h5, and pool_design strictly requires 4D. A 1-line
  patch in _iter_design_activations (expand_dims to 4D when 3D) would
  unlock them; left as a follow-up.

  The README at tutorials/classifiers/README.md reproduces the whole
  pipeline in 6 bash commands.