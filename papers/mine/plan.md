# NeurIPS Submission Plan — 7 Days

**Paper**: Interpretable Biosecurity Screening via Sparse Autoencoders on Protein Design Models
**Deadline**: 7 days from 2026-04-30 → **2026-05-07**
**Current AUROC**: 0.817 ± 0.10 (homology-clustered) vs SOTA 0.92 (DTVF)

---

## Core Thesis (Do Not Change)

The paper is NOT a AUROC race. The contribution is:

> *First application of SAEs to protein design models for interpretable biosecurity screening — providing structural, feature-level explanations for hazard predictions that black-box classifiers cannot.*

DTVF is a comparison point, not the goal. The framing is: "We approach SOTA without any task-specific training, purely through interpretability, while unlocking structural explanations DTVF cannot provide."

The unique selling points in order:
1. First SAE application to an all-atom diffusion model (RFD3) and to biosecurity
2. Feature-level structural explanations — which residues/motifs drive the prediction
3. Generalizes across threat categories (virulence + immunogenicity with VaxiJen)
4. Opens the door to runtime guardrails and steering, not just post-hoc classification

---

## 7-Day Schedule

### Day 1–2 (Apr 30 – May 1): Experiments to strengthen results

**Goal**: Push AUROC closer to 0.87+ on clustered split, add a second task.

#### 1a. Expand to deeper layers
Currently using blocks 6, 8, 12 for RFD3. saeber.md shows AUROC and feature quality
increase monotonically with depth. Add blocks 16, 20, 24 (or the last 2–3 blocks available
in RFD3). Modify `foundry collect` to add new hookpoints.

Expected gain: +0.03–0.05 AUROC based on observed depth trend.

#### 1b. Ensemble RF3 + RFD3 features
Concatenate the best-block SAE features from RF3 and RFD3 before fitting the logistic
regression probe. Two structurally diverse views of the same protein should be
complementary. Run via the existing `detectors fit` pipeline with a new `ConcatExtractor`.

Expected gain: +0.02–0.04 AUROC; also strengthens the paper's claim that the framework
generalizes across model families.

#### 1c. Feature selection before probe
Currently feeding all 12288 SAE features into logistic regression. With n=220, this is
severely underdetermined. Use `detectors score` AUROC scores to select top-K features
(K ∈ {50, 100, 200, 500}) before fitting. SelectKBest + LR is a one-line sklearn change.

Expected gain: +0.02–0.05 AUROC; reduces variance, tightens error bars.

#### 1d. Expand dataset with VFDB
VirulentFactorDatabase (VFDB) has labeled categories (toxin, effector, adhesin, etc.).
Add sequences from VFDB as additional positives. This increases n from 275 toward 500+
AND enables per-category AUROC breakdown — a compelling new result that addresses the
"no category labels" limitation directly.

Use `data_pipelines` to pull, filter by length <300, rerun mmseqs2 clustering, rerun
activate collection with the same hooks.

Expected gain: higher n → tighter error bars; VFDB categories → new qualitative result.

#### 1e. VaxiJen probe (second task)
`data_pipelines/vaxijen/` already exists. Run the same logistic regression probe pipeline
on VaxiJen immunogenicity labels. This adds a second empirical result showing the
framework transfers across threat categories beyond virulence.

This turns a single-task paper into a multi-task interpretability framework paper —
much stronger position.

---

### Day 3 (May 2): Deepen interpretability story

This is the section that makes the paper stand out. Do NOT skip it to focus on AUROC.

#### 3a. Diff-of-means feature vectors
For each model/layer, compute mean activation over positive class minus mean over negative
class. Visualize top-20 features as a bar chart. This gives a publication-quality figure
showing which features systematically shift between virulent and benign proteins.

#### 3b. PyMOL structural heatmaps (4–6 curated examples)
Pick 2–3 virulent proteins where the top hazard feature fires strongly. Render PyMOL
heatmaps per-residue. Annotate manually or with VLM (GPT-4o / Claude): "feature 7341
fires on the beta-barrel pore-forming domain of toxin X." These figures ARE the paper's
contribution made tangible.

#### 3c. Feature AUROC vs. layer depth plot
Already partially done. Make it a clean figure: x=layer, y=top-5 feature AUROC, separate
lines for RFD3 and RF3. Shows the depth-interpretability trend is systematic and
model-agnostic.

---

### Day 4 (May 3): Writing — Introduction, Related Work, Methods

Frame the narrative. Key points:

- **Opening hook**: Protein design models could lower the barrier to bioweapon design.
  Existing screens (BLAST, structural homology) are opaque and sequence-limited.
- **Gap**: No prior work applies mechanistic interpretability to protein design models
  for biosecurity.
- **Contributions** (enumerate clearly):
  1. First SAEs trained on RFD3 and RF3
  2. Feature-correlated-with-virulence database
  3. Interpretable probe approaching SOTA on virulence classification
  4. Zero-shot transfer to immunogenicity (VaxiJen)
  5. Open harness (foundry) for reproducibility

Related work must clearly position against:
- FoldSAE (SAEs on older RFDiffusion, only secondary structure features, not biosecurity)
- InterProt / InterPLM (PLMs, not diffusion, not biosecurity)
- Goodfire MatterGen (diffusion but materials, not biology or biosecurity)
- DTVF / VirulentHunter (biosecurity classifiers, but black-box, no structural explanation)

The 2x2 quadrant figure (interpretable vs. performant, diffusion model vs. PLM) is a
good way to show our position is unique.

---

### Day 5 (May 4): Writing — Experiments, Results, Figures

- Finalize all result tables with updated AUROC numbers
- Figure 1: probe AUROC heatmap (model × layer × raw/SAE × split) — already exists
- Figure 2: AUROC vs. depth line chart (RFD3 vs. RF3)
- Figure 3: Top individual features bar chart (AUROC ranking, with BH-corrected q-values)
- Figure 4: PyMOL structural heatmaps for 2–3 exemplar virulent proteins
- Figure 5 (if VaxiJen done): side-by-side AUROC for virulence vs. immunogenicity
- Table 1: Comparison with DTVF, VirulentHunter, DeepVF, VF-Pred

Emphasize in the text:
- "SAE outperforms raw activations at block 12 by +0.054 AUROC — we hypothesize this
  reflects polysemanticity untangling at deeper layers, an effect worth further study"
- "Our method requires no labeled biosecurity training data for the base model"

---

### Day 6 (May 5): Discussion, Limitations, Ethics, Polish

#### Limitations to acknowledge honestly:
- Small dataset (n=275 → ~500 with VFDB)
- Compute-forced sequence length cap (<300 residues)
- No causal intervention experiments (steering/ablation)
- SAE feature labels require expert interpretation

#### Ethics section (NeurIPS requires this):
This is dual-use research. Write a clear ethics statement:
- Dual-use risk: these features could theoretically inform design
- Mitigation: guardrails framing, not generation assistance
- Comparison to existing public tools (BLAST, HHblits) which have same dual-use concern
- Follow the Responsible Disclosure / Asilomar norms framing

NeurIPS reviewers will scrutinize this given the biosecurity topic. Write it carefully.

#### Future work to highlight:
- Runtime guardrail: terminate diffusion trajectories when hazard features activate
- Steering: use identified features to steer away from dangerous latent directions
- Scale: larger dataset (full SafeProtein, VFDB), longer sequences with more compute
- Neuronpedia-style feature database for biology models

---

### Day 7 (May 6): Final pass, formatting, submission

- NeurIPS 2025 template, 9 pages + references
- Proofread abstract, check every number matches tables
- Ensure reproducibility section mentions foundry repo + dataset DOI (HuggingFace)
- Submit by end of day, May 6 (one day buffer before deadline)

---

## Venue Strategy

**Primary**: NeurIPS 2026 main track. Competitive but plausible given novelty of contribution.

**Fallback A** (hedge now, don't wait for rejection):
- NeurIPS workshop: "AI for Science" or "Generative and Experimental Perspectives for Biomolecular Design" 
- These are peer-reviewed but lower bar; can run parallel to main track submission

**Fallback B** (if main track rejected):
- ICLR 2027 (more time to strengthen with wet lab validation)
- Nature Machine Intelligence / Bioinformatics (journal, no deadline pressure)

The biosecurity + interpretability intersection is highly relevant to NeurIPS's new
emphasis on AI safety. Lean into that framing — this is AI safety research applied to
computational biology.

---

## What NOT to Do

- Do not try to reach 0.92 AUROC at the cost of the interpretability story
- Do not add wet lab experiments you cannot complete — acknowledge limitation honestly
- Do not expand scope to toxicity or antibiotic resistance unless it takes <1 day
- Do not submit to a venue that requires >9 pages if you cannot fill it with solid results

---

## AUROC Gap Mitigation Summary

| Action | Expected Gain | Effort |
|--------|--------------|--------|
| Deeper layers (16, 20, 24) | +0.03–0.05 | Low — existing pipeline |
| Feature selection (top-K) | +0.02–0.05 | Low — 1 param sweep |
| RF3+RFD3 ensemble | +0.02–0.04 | Medium — new extractor |
| VFDB dataset expansion | +0.02 + tighter CI | Medium — new data pipeline |
| VaxiJen second task | Paper scope, not AUROC | Low — pipeline exists |

If all four land, realistic target is **0.86–0.90 clustered AUROC**, which is within error
bars of DTVF and makes the comparison much more defensible. Even at 0.82, the paper is
publishable — the framing just needs to be right.
