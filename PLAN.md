● Where to train SAEs

  Primary target: residual stream of
  DiffusionTransformer (the 18-layer
  LocalTokenTransformer)

  - File: models/rfd3/src/rfd3/model/layers
  /blocks.py — class LocalTokenTransformer
  (~L585)
  - Hook: output of each
  StructureLocalAtomTransformerBlock —
  tensor A_I of shape [B, I, 768]
  - This is the deepest stack (18 blocks),
  runs per diffusion timestep inside
  RFD3DiffusionModule, and is the cleanest
  analogue to an LLM residual stream. It's
  per-residue, semantically rich (post
  atom→token aggregation), and shape-stable
   across layers.

  Which layer: borrowing from LLM SAE
  practice, start with a middle-to-late
  layer (e.g., block 12 of 18) — features
  tend to be most abstract and linearly
  decodable there. Early layers will be
  dominated by embedding/positional
  signals; the final layer is
  over-specialized for the coordinate
  update head.

  Secondary: S_I (sequence track, c_s=384)
  at the DiffusionTokenEncoder / recycler
  interface — useful if you want features
  tied to sequence identity rather than
  structural context. Skip Z_II (pair)
  initially — it's quadratic and awkward to
   dictionary-learn.

  Timestep conditioning matters.
  Activations at high σ (noisy) vs. low σ
  (near-clean) encode very different
  things. Either (a) train one SAE
  conditioned on timestep bin, or (b) train
   separate SAEs on early/mid/late
  denoising steps. I'd recommend (b) for a
  first paper — cleaner story.

  Interesting features (candidates for X,
  Y, Z)

  Ranked by a mix of scientific interest
  and validation tractability:

  Tier 1 — easy to validate, likely to
  exist:
  - Secondary structure (helix / sheet /
  loop) — gold standard sanity check; DSSP
  gives ground truth per residue
  - Solvent exposure / core-vs-surface —
  you already have ref_atomwise_rasa as a
  regression target
  - Motif vs. scaffold token identity —
  should fall out trivially from
  is_motif_token_with_fully_fixed_coord;
  good as a "the method works" baseline

  Tier 2 — scientifically interesting, the
  real paper:
  - Binding interface / hotspot geometry —
  maps to is_atom_level_hotspot
  conditioning, directly steerable, wet-lab
   testable via binding assays
  - H-bond donor/acceptor placement —
  active_donor / active_acceptor are
  already in the conditioning; check
  whether SAE features carve this out
  spontaneously
  - Ligand pocket features — pocket lining
  residues, pocket volume/shape;
  validatable with docking + the
  NAI/ACT/OQO examples in the demo
  - Chain-break / oligomer-interface
  features — /0 separators in contigs
  - Nucleic-acid-adjacent residues — dsDNA
  binder case (ref_motif_token_type,
  ori_token)

  Tier 3 — ambitious, higher variance:
  - Fold-class features (TIM barrel,
  Rossmann, ferredoxin, etc.) — would need
  curated eval set; very compelling if they
   exist
  - Symmetry-axis features for oligomeric
  designs
  - Disorder / flexibility propensity —
  harder ground truth

  Steerability benchmarks (for the baseline
   comparison)

  Concrete candidates: steer % helix
  content, induce/suppress
  binding-competent poses at a hotspot,
  enforce β-sheet over helix at fixed
  positions. All three admit simple
  linear-probe and fine-tuning baselines
  and have objective structural metrics,
  which matches your abstract's benchmark
  claim.

  Suggested X, Y, Z for the abstract

  Pick one from each tier for a clean
  story: (X) secondary structure, (Y)
  hotspot/interface geometry, (Z)
  ligand-pocket features — covers the three
   design regimes shown in demo.json
  (unconditional, motif scaffolding,
  small-molecule binders) and lets the
  wet-lab piece target the enzyme/binder
  case.