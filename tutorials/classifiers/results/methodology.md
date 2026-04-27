# Methodology

## Models and tooling

We used the foundry repository from RosettaCommons to run RF3 (folding) and RFDiffusion3 (RFD3, partial diffusion). To collect activations during inference, we extended the existing `engine.py` for both models so that user-supplied hook configs in the inputs JSON get registered as `register_forward_hook` callbacks on the corresponding torch modules. The hook implementation lives in `sae/src/sae/activation_buffer.py`. Each call writes its tensor (after detaching to CPU and float32) into a buffer that flushes to an HDF5 file every N collected activations. Static hooks fire once per design, dynamic hooks fire every diffusion step and are subsampled by `collect_every_n_steps`.

The model code we used is at https://github.com/RosettaCommons/foundry/tree/production/models/rfd3 and https://github.com/RosettaCommons/foundry/blob/production/models/rf3/README.md.

## Datasets

For virulence we used SafeProtein (viral entries only) as the positive class. For length-matched negatives we queried UniProt with the filter `NOT KW-0800 NOT KW-0843 NOT taxonomy_id:10239 AND length:100 TO 300`, which excludes entries annotated as toxic or pathogenic and excludes viral taxonomy. We restricted both classes to sequences under 300 residues to keep memory usage tractable on a single L40 GPU. After this filter the labelled set is **165 hazards / 110 benigns = 275 designs**.

For toxicity we used ToxinPred3 (1200 train, 400 test peptides, 19 to 35 amino acids, balanced classes), which already ships its own train/test split.

PDB structures for the SafeProtein and UniProt benign sets came from the canonical UniProt-to-PDB mappings, downloaded with our `download_safeprotein.sh` and `download_uniprot_pdb_benigns.sh` scripts. Each design is uniquely keyed by `<class>_<accession>` (`hazard_P49121`, `benign_O00287`, etc.).

## Activation collection

For RF3 we fold the input sequence. For RFD3 we noise the input PDB by `partial_t=5` angstroms and run the reverse trajectory back, which gives an activation distribution close to what the model would see if denoising toxin- or virus-resembling proteins from scratch. We chose 5 angstroms because it perturbs the structure enough to engage the denoising machinery while still keeping the trajectory anchored to the source motif, so the per-design activations stay tied to that motif rather than drifting toward unconditional generation.

For each model we hook three layers spread along the diffusion transformer at roughly 25%, 50%, and 75% depth. For RFD3 these are blocks 6, 8, and 12; for RF3 they are blocks 12 and 16. This follows the multi-layer probing strategy from Bussmann et al. 2025, which found that the most discriminative layer for downstream classification varies by task and is hard to predict a priori.

The resulting activation tensors have shape `(n_samples, n_steps, n_tokens, hidden_dim)` per design, where `hidden_dim` is 768 for the block hooks. Token count equals residue count for these full-protein designs. Metadata pickles, generated CIF files, and the JSON specification are written next to the h5 so downstream interpretability can fetch atom arrays and structures by design id.

## Sparse autoencoders

We trained one Matryoshka BatchTopK SAE per (model, hook) cell using the existing trainer in `sae/src/sae/train.py`. Hyperparameters were the package defaults: `dict_size=12288`, `k=80`, group fractions `[0.0625, 0.125, 0.1875, 0.25, 0.375]`, 20k training steps, logspaced checkpointing. We picked Matryoshka BatchTopK because the nested group structure prevents feature absorption (a smaller group is forced to learn coarse features without "borrowing" capacity from the larger groups) and BatchTopK gives a clean, threshold-free sparsity guarantee at inference time.

A health check at `tutorials/classifiers/sae_health_check.py` confirmed all five SAEs are well-trained: l0 close to k (so the sparsity constraint binds as designed), `frac_alive` between 0.94 and 1.00 (essentially no dead features), fraction of variance explained above 0.96, cosine similarity above 0.98.

## Labelling

Labels are derived from the design id prefix in the activations h5 rather than from the original sources CSV. The mapping is:

```
hazard_*    -> 1   (SafeProtein viral)
benign_*    -> 0   (UniProt benign)
train_pos_* -> 1   (ToxinPred3 toxic)
train_neg_* -> 0   (ToxinPred3 non-toxic)
```

The h5 is the source of truth because the upstream sources file can drift if entries fail in collection or get filtered post-hoc. The script that writes the labels CSV is `tutorials/classifiers/build_rfd3_labels.py`. It also serves as a sanity check, since any design id with an unknown prefix is logged and skipped.

## Probe pipeline

We train logistic regression probes (pure torch implementation in `detectors/src/detectors/classifiers/logistic.py`, BCE with L2 weight decay, Adam, 75 to 300 epochs depending on variant) on per-design feature vectors. There are two extractors:

* **identity** uses the raw activations directly. Feature dim is 768 per token.
* **sae_encode** runs each per-token activation through the trained SAE encoder. Feature dim is 12288 (the dictionary size).

Pooling reduces the per-design tensor `(n_samples, n_steps, n_tokens, F)` to `(n_samples, F)` by selecting the last diffusion step and averaging across tokens, then averaging across samples. We use `select_top_k=50` to restrict the LR to the 50 features with highest univariate AUROC on the training fold; this is computed inside `detect fit` and saved with the bundle so the same indices are used at evaluation.

One pipeline detail worth flagging: the SAE encoder runs on the raw per-token activations and pooling happens after encoding. The opposite order (pool first, encode the pooled vector) is wrong for a TopK SAE because the pooled vector is far out of distribution; in our case it dropped feature utilization from 81% to under 1%. We caught this with the SAE health check and fixed it in `detectors/pipelines/cache.py`.

## Folds and the train/test split

The split happens once, in `tutorials/classifiers/split_labels.py`, well before any LR training. We do five-fold stratified cross-validation. The splitter groups designs by `(label, source-prefix)` and round-robins each stratum across the five folds, so every fold's test set has the same class ratio and the same mix of hazard accessions. The output is ten CSVs per dataset:

```
labels_fold0_train.csv   labels_fold0_test.csv
labels_fold1_train.csv   labels_fold1_test.csv
...
labels_fold4_train.csv   labels_fold4_test.csv
```

For the SafeProtein cells, n=275 splits into roughly 220 train and 55 test per fold. For ToxinPred3, n=1200 splits into 960 train and 240 test per fold.

The LR code itself is fold-agnostic. It just trains on whatever labels CSV is passed via `labels_path`. The activations h5 is the same across all folds; what changes per fold is which `design_id`s the labels CSV contains. `attach_labels` in `detectors/src/detectors/pipelines/labeled.py` filters the cached features down to the ones present in the current labels file before the LR sees them.

We also generated a homology-clustered version of the splits using mmseqs2 easy-cluster at 30% sequence identity. The same `split_labels.py` writes `labels_foldN_{train,test}_cluster.csv` files alongside the random ones. Under cluster splits, each fold drops entire clusters into the test set, so paralogs from training cannot leak into test. Cluster folds are slightly uneven in size because clusters are uneven (54 to 59 test designs per fold for the SafeProtein cells).

## Sweep variants

We ran three variants of the probe sweep:

| variant | split | weight_decay | epochs | select_top_k |
|---|---|---|---|---|
| baseline | random | 1e-4 | 300 | 50 (SAE only) |
| cluster | homology-clustered | 1e-4 | 300 | 50 (SAE only) |
| stop_overfitting | random | 1e-2 | 75 | 50 (both extractors) |

The original asymmetric `select_top_k` (only on SAE) gave SAE an unfair regularization advantage in the SAE-vs-raw comparison. We added the symmetric variant to remove this confound, alongside the heavier weight decay and shorter training for the overfitting fix. Each variant produces 70 LR fits: 14 (dataset, hook, extractor) cells times 5 folds. Total across all three variants is 210 LR fits.

Configs are generated by `tutorials/classifiers/generate_configs.py`, which reads four environment variables (`CLASSIFIER_RUN_TAG`, `CLASSIFIER_LABELS_TAG`, `CLASSIFIER_WEIGHT_DECAY`, `CLASSIFIER_EPOCHS`, `CLASSIFIER_SELECT_TOP_K`) so different variants produce different output directories without touching code. The sweep itself is `bash tutorials/classifiers/sweep_probes.sh` which loops over the generated yaml configs and dispatches to `detect fit` and `detect evaluate`.

## Aggregation

`tutorials/classifiers/aggregate_metrics.py` globs all `metrics.json` files under a sweep root, parses the cell name to extract `(dataset, model, hook, extractor, fold)`, and computes mean and standard deviation of every numeric metric across folds. Output is a markdown table per variant. Any cell with fewer than 5 successful folds shows up with a smaller `n_folds` value, which surfaces missing or crashed runs.

## Per-feature attribution

Independent of the probe sweep, we score every SAE feature against the full labels CSV (no train/test split) using univariate AUROC. The pipeline is in `detectors/src/detectors/scorers/`. For the top-200 features by `|AUROC - 0.5|` we also compute Mann-Whitney U p-values, then apply Benjamini-Hochberg FDR correction to all non-constant features to get q-values. Multiple-testing correction matters here because the dictionary has 12288 features and most do not actually carry class information; without BH the raw p-values would overstate significance.

The output is one parquet per (dataset, hook) cell with columns `feature_id, auroc, auroc_p, q_value, n_samples`. We treat features with `q < 0.05` as discoveries.

## Visualization

For the top hazard-firing features we render PyMOL scripts that highlight the residues where the feature fires most strongly. The renderer at `tutorials/classifiers/visualize_features.py` reads the CIF file generated by `saffron collect`, parses it with biotite, and maps token index to (chain, residue) by chain order. It writes a `.pml` script per (feature, design, sample) that can be rendered to PNG with `pymol -cq`. The batch wrapper at `tutorials/classifiers/render_top_features.sh` reads `top_features.csv` and runs the renderer for the top hazard-firing SAE features per (dataset, hook).

We chose to map token to residue via chain order rather than by reading a token-to-residue mapping from a separate metadata file because the rfd3_partial collection did not write the metadata pickles that `sae/evaluation/iter_design_activations` expects. For full-protein partial diffusion this is safe: token count equals residue count and ordering matches.

## What did not work

Three things tripped us up.

The first was the SAE encoding order. We initially pooled activations across tokens and steps, then encoded the pooled vector through the SAE. This silently produced sparse-looking results (only about 1% of features fired) and made the SAE-vs-raw probe comparison meaningless. The fix was to encode every token through the SAE first, then pool the encoded sparse features. The SAE health check caught this; the patch is in `detectors/pipelines/cache.py`.

The second was the eval activations h5 for ToxinPred3. The ToxinPred3 dataset ships an upstream train/test split (1200 train sequences, 400 test sequences), and the original baseline pipeline used this directly: fit on the train h5, evaluate on the test h5. When we moved to k-fold cross-validation, the test labels CSV started containing `train_pos_*` and `train_neg_*` design ids drawn from the train h5, but the eval pipeline still pointed at the test h5 (whose ids are `test_pos_*` and `test_neg_*`). Zero overlap, n_designs=0, AUROC silently defaulted to 0.5. The fix in `generate_configs.py:_emit_eval` is to always read from `dataset["activations"]` and ignore the upstream test h5 once k-fold is in play.

The third was forgetting that token initializer outputs (and `to_si` for RF3) come out as 3D tensors per step in the h5 rather than 4D. Our pooling code requires 4D and crashes on these hooks. We worked around it by skipping these hooks in the sweep; a one-line `np.expand_dims` patch in `_iter_design_activations` would unlock them, which is on the followup list.

## Reproduction

The full pipeline is reproducible from `tutorials/classifiers/README.md`. The short version:

```bash
# 1. labels
python tutorials/classifiers/build_rfd3_labels.py --activations <h5> --hook block12 --out <labels.csv>

# 2. folds
python tutorials/classifiers/split_labels.py --labels <labels.csv> --out-dir <dir> --n-folds 5

# 3. configs (env vars control variant)
python tutorials/classifiers/generate_configs.py

# 4. probes
bash tutorials/classifiers/sweep_probes.sh

# 5. attribution (Q2)
bash tutorials/classifiers/sweep_scores.sh

# 6. aggregate
python tutorials/classifiers/aggregate_metrics.py --sweep-root outputs/classifiers --out tutorials/classifiers/results

# 7. render top features as PNGs
bash tutorials/classifiers/render_top_features.sh
```
