❯ what is partial_t originally used for by researchers? ny interp trajectory use
  case is probably strange

● Honest answer: yes, your use case is offbeat. The standard uses are all
  output-oriented (the final structure is what matters). You're treating the model
  as a probe to get activations, which is more like image-diffusion interp work than
   typical protein design.

  Canonical uses of partial_t in protein design:

  ┌──────────────────────────────┬─────────────┬────────────────────────────────┐
  │           Use case           │  partial_t  │         What you keep          │
  ├──────────────────────────────┼─────────────┼────────────────────────────────┤
  │ Diversification — given a    │             │ Same fold/binder, slightly     │
  │ good design, generate 100    │ 3–8 Å       │ different backbone — explores  │
  │ close variants               │             │ nearby designable space        │
  ├──────────────────────────────┼─────────────┼────────────────────────────────┤
  │ Refinement — clean up        │             │ Fix local geometry without     │
  │ clashes/strain in a coarse   │ 1–4 Å       │ changing topology              │
  │ or imperfect design          │             │                                │
  ├──────────────────────────────┼─────────────┼────────────────────────────────┤
  │ Loop redesign — hold most of │ 5–10 Å on   │ Same scaffold, alternative     │
  │  the protein fixed (via      │ loops only  │ loop conformations             │
  │ contig) and resample loops   │             │                                │
  ├──────────────────────────────┼─────────────┼────────────────────────────────┤
  │ Symmetric oligomer nudging — │             │ Alternative quaternary         │
  │  perturb one subunit and     │ 4–8 Å       │ geometries of the same complex │
  │ propagate via symmetry       │             │                                │
  ├──────────────────────────────┼─────────────┼────────────────────────────────┤
  │ Side-chain repacking around  │ 2–5 Å       │ Same backbone, different       │
  │ a site                       │             │ rotamer states                 │
  ├──────────────────────────────┼─────────────┼────────────────────────────────┤
  │ Native-sequence backbone     │             │                                │
  │ diversification — produce    │ 5–10 Å      │ Sequence-consistent backbone   │
  │ ensembles for                │             │ variants                       │
  │ docking/screening            │             │                                │
  └──────────────────────────────┴─────────────┴────────────────────────────────┘

  These are all in the original RFdiffusion paper (Watson et al. 2023) and used
  routinely in the IPD's design pipelines. The user gives the model a structure they
   like, partially noises it, and asks the model to "project it back onto the
  manifold of realistic proteins" — getting either a cleaner version or a
  near-neighbor variant.

  Your interp use case is different in kind:
  - You're not asking for a designed output — you're asking for trajectory
  activations
  - Partial_t is being used as a "conditioning lever" so the activations carry
  signal about the input structure, not because you care what gets emitted
  - You're treating the diffusion process as an encoder-with-probes, which
  protein-design researchers basically don't do

  Closest precedents I know of:
  - Image diffusion interp (Diffusion Lens, Concept Sliders, h-space probing on
  Stable Diffusion) — they extract features from intermediate denoising states to
  study/steer generation. Same idea, different domain.
  - Folding-trajectory probing on AF2/ESMFold — a small body of work runs linear
  probes on intermediate recycle outputs. Closer to the protein side, but the model
  is a folding model, not a design model.
  - AlphaFold 2 representation analyses — use embeddings as features for downstream
  tasks (toxin/effector prediction, etc.). Same "use the model as a featurizer"
  spirit, but on a static representation, not a trajectory.

  Why the protein-design community hasn't done this much:
  - Diffusion-design SAEs are themselves new (the trained SAEs at
  outputs/sae/2026-04-20_05-38-45/ are recent foundry work).
  - Most protein interp work has gone after PLMs (ESM2/3) where the input→activation
   mapping is direct and there's no trajectory to think about.
  - Partial diffusion specifically has been an output-shaping tool, not a featurizer
   — nobody had a reason to think of it as one until SAE-feature classifiers became
  plausible.

  So your framing isn't wrong; it's just novel. It's actually a fairly clean move:
  partial_t gives you a tunable knob that interpolates between "pure folding-like
  behavior" (low t) and "pure design behavior" (high t), which is exactly the right
  thing for a study of how design behavior diverges from folding when the model is
  conditioned on a hazardous structure. That'd be a paper-shaped angle if the
  classifier numbers come out interesting.