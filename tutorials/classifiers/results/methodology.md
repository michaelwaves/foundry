# Methodology

## Models and tooling

We used the foundry repository from RosettaCommons to run RF3 (folding) and RFDiffusion3 (RFD3, partial diffusion). To collect activations during inference we extended each model's `engine.py` so that user-supplied hook configs in the inputs JSON get registered as `register_forward_hook` callbacks on the corresponding torch modules. The hook implementation is at `sae/src/sae/activation_buffer.py`. Each call detaches the tensor to CPU float32 and writes to an HDF5 file, flushing every N activations. Source for the models: https://github.com/RosettaCommons/foundry/tree/production/models/rfd3 and https://github.com/RosettaCommons/foundry/blob/production/models/rf3/README.md.

## Dataset

For virulence we used SafeProtein (viral entries only) as the positive class. For length-matched negatives we queried UniProt with `NOT KW-0800 NOT KW-0843 NOT taxonomy_id:10239 AND length:100 TO 300` to exclude entries annotated as toxic or pathogenic and exclude viral taxonomy. We restricted both classes to under 300 residues to fit on a single L40 GPU. The labelled set is **165 hazards and 110 benigns, 275 designs total**. PDB structures came from canonical UniProt-to-PDB mappings via `download_safeprotein.sh` and `download_uniprot_pdb_benigns.sh`. Each design is keyed by `<class>_<accession>` (e.g. `hazard_P49121`, `benign_O00287`).

## Activation collection

For RF3 we fold the input sequence. For RFD3 we noise the input PDB by `partial_t=5` angstroms and run the reverse trajectory back. This gives an activation distribution close to what the model would see when denoising toxin-like proteins from scratch, while staying anchored enough to the source motif that per-design activations stay tied to that motif rather than drifting toward unconditional generation.

We hook three layers spread along the diffusion transformer at roughly 25%, 50%, and 75% depth: blocks 6, 8, 12 for RFD3 and blocks 12, 16 for RF3. This follows the multi-layer probing strategy from Bussmann et al. 2025, who found that the most discriminative layer for downstream classification varies by task and is hard to predict. Activation tensors come out as `(n_samples, n_steps, n_tokens, 768)` per design.

## Sparse autoencoders

One Matryoshka BatchTopK SAE per (model, hook), trained with the package defaults: `dict_size=12288`, `k=80`, group fractions `[0.0625, 0.125, 0.1875, 0.25, 0.375]`, 20k steps, logspaced checkpointing. We chose Matryoshka BatchTopK because the nested group structure prevents feature absorption (smaller groups are forced to learn coarse features without borrowing capacity from the larger groups) and BatchTopK gives a clean threshold-free sparsity guarantee at inference. A health check at `tutorials/classifiers/sae_health_check.py` confirmed all SAEs are well-trained: l0 close to k, `frac_alive` between 0.94 and 1.00, FVE above 0.96, cosine similarity above 0.98.

## Labelling

Labels come from the design id prefix in the activations h5 (`hazard_*` is 1, `benign_*` is 0), not from the upstream sources CSV, since the sources file can drift if entries fail in collection or get filtered post-hoc. Built by `tutorials/classifiers/build_rfd3_labels.py`.

## Probe pipeline

Logistic regression probes (pure torch, BCE with L2 weight decay, Adam) on per-design feature vectors. Two extractors:

* **identity** uses raw activations (768-dim).
* **sae_encode** runs each per-token activation through the trained SAE encoder (12288-dim).

Pooling reduces `(n_samples, n_steps, n_tokens, F)` to `(n_samples, F)` by selecting the last diffusion step, averaging over tokens, then averaging over samples. We use `select_top_k=50` to restrict the LR to the 50 features with highest univariate AUROC on the training fold. The selected indices are saved with the bundle so the same features are used at evaluation.

A pipeline detail worth flagging: the SAE encoder runs on per-token activations and pooling happens after encoding. The opposite order (pool first, encode the pooled vector) is wrong for a TopK SAE because the pooled vector is far out of distribution; in our case it dropped feature utilization from 81% to under 1%. We caught this with the SAE health check and fixed it in `detectors/pipelines/cache.py`.

## Folds and the train/test split

We do five-fold stratified cross-validation. The splitter at `tutorials/classifiers/split_labels.py` groups designs by `(label, source-prefix)` and round-robins each stratum across the five folds, so every fold's test set has the same class ratio and the same source mix as the full set. The output is ten CSVs per dataset:

```
labels_fold0_train.csv   labels_fold0_test.csv
labels_fold1_train.csv   labels_fold1_test.csv
...
labels_fold4_train.csv   labels_fold4_test.csv
```

For SafeProtein, n=275 splits into 220 train and 55 test per fold. The LR code itself is fold-agnostic. It just trains on whatever labels CSV is passed via `labels_path`. The activations h5 stays the same across all folds; what changes is which design ids the labels CSV contains. `attach_labels` in `detectors/src/detectors/pipelines/labeled.py` filters the cached features down to the design ids present in the current labels file.

We also generated a homology-clustered version of the splits using mmseqs2 easy-cluster at 30% sequence identity. The same script writes `labels_foldN_{train,test}_cluster.csv` files alongside the random ones. Under cluster splits, each fold drops entire clusters into the test set so paralogs cannot leak from train into test. Cluster folds are slightly uneven in size (54 to 59 test designs) because clusters are uneven.

## Sweep variants

We ran three variants of the probe sweep:

| variant | split | weight_decay | epochs | select_top_k |
|---|---|---|---|---|
| baseline | random | 1e-4 | 300 | 50 (SAE only) |
| cluster | homology-clustered | 1e-4 | 300 | 50 (SAE only) |
| stop_overfitting | random | 1e-2 | 75 | 50 (both extractors) |

The original asymmetric `select_top_k` gave SAE an unfair regularization advantage in the SAE-vs-raw comparison. The symmetric variant removes this confound, alongside heavier weight decay and shorter training to address overfitting. Each variant produces 50 LR fits: 5 (model, hook, extractor) cells from RFD3 plus 4 from RF3 times 5 folds.

Configs are emitted by `tutorials/classifiers/generate_configs.py`, controlled by `CLASSIFIER_RUN_TAG`, `CLASSIFIER_LABELS_TAG`, `CLASSIFIER_WEIGHT_DECAY`, `CLASSIFIER_EPOCHS`, and `CLASSIFIER_SELECT_TOP_K` so different variants live in separate directories without code changes. The sweep is `bash tutorials/classifiers/sweep_probes.sh`.

## Aggregation

`tutorials/classifiers/aggregate_metrics.py` globs all `metrics.json` files under a sweep root, parses cell names into `(dataset, model, hook, extractor, fold)`, and computes mean and standard deviation across folds. Output is a markdown table per variant.

## Per-feature attribution

Independent of the probe sweep, we score every SAE feature against the full labels CSV using univariate AUROC. For the top-200 features by `|AUROC - 0.5|` we compute Mann-Whitney U p-values, then apply Benjamini-Hochberg FDR correction across all non-constant features to get q-values. BH correction matters because the dictionary has 12288 features and most carry no class information; without it the raw p-values would overstate significance. We treat features with `q < 0.05` as discoveries.

## Visualization

For the top hazard-firing features we render PyMOL scripts that highlight residues where the feature fires most strongly. The renderer at `tutorials/classifiers/visualize_features.py` reads the CIF generated by `saffron collect`, parses it with biotite, and maps token index to (chain, residue) by chain order. Token count equals residue count for our full-protein partial-diffusion designs so this mapping is safe. The batch wrapper `tutorials/classifiers/render_top_features.sh` reads `top_features.csv` and renders the top hazard-firing features per (dataset, hook).

## What did not work

Pool-then-encode silently broke the SAE arm. We initially pooled activations across tokens and steps, then ran the pooled vector through the SAE encoder. Only about 1% of dictionary features fired and the SAE-vs-raw comparison was meaningless. The fix was to encode every token first, then pool the encoded sparse features. The patch is in `detectors/pipelines/cache.py`. The SAE health check is what flagged it.

## Reproduction

```bash
python tutorials/classifiers/build_rfd3_labels.py --activations <h5> --hook block12 --out <labels.csv>
python tutorials/classifiers/split_labels.py --labels <labels.csv> --out-dir <dir> --n-folds 5
python tutorials/classifiers/generate_configs.py        # env vars control variant
bash   tutorials/classifiers/sweep_probes.sh            # Q1
bash   tutorials/classifiers/sweep_scores.sh            # Q2
python tutorials/classifiers/aggregate_metrics.py --sweep-root outputs/classifiers --out tutorials/classifiers/results
bash   tutorials/classifiers/render_top_features.sh
```
