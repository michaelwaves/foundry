What you already have:
  - hazard_inputs_ablate_f639 — ablation of feature 639 on 2
  hazard designs (P00626, P11407), 8 samples each
  - benign_inputs_diff_alpha3 — raw_diff steer on 2 benign
  designs
  - benign_inputs_f639_alpha5 — SAE feature steer on 2 benign
  designs

  What's missing:

  Step 1 — Null baseline run (unsteered hazard inputs)

  You need the same hazard inputs with zero steering to compare
  against:
  saffron collect model=rfd3 \
    inputs=tutorials/steering/configs/null_block12_f639.json \
    hooks=rfd3_partial \
    out_dir=outputs/steering/sweep/alpha0

  Step 2 — α sweep on hazard inputs with ablation

  Create 3 new steering configs for different strengths (copy
  ablate_block12_f639.yaml, change alpha):

  ┌──────────┬───────┐
  │   run    │ alpha │
  ├──────────┼───────┤
  │ existing │ 1.0   │
  ├──────────┼───────┤
  │ new      │ 2.0   │
  ├──────────┼───────┤
  │ new      │ 4.0   │
  ├──────────┼───────┤
  │ new      │ 8.0   │
  └──────────┴───────┘

  for alpha in 2.0 4.0 8.0; do
    saffron steer model=rfd3 \
      inputs=tutorials/steering/configs/ablate_block12_f639.json
  \
      "steering.block12[0].alpha=$alpha" \
      out_dir=outputs/steering/sweep/alpha${alpha}
  done
  (Check first whether Hydra override syntax works for nested
  list keys — if not, create 3 separate YAML configs.)

  Step 3 — Collect activations for each run

  Each saffron steer run should also collect activations so you
  can score them with the probe. Add hooks=rfd3_partial to every
  steer command above.

  Step 4 — Screen each run with the probe

  for alpha in 0 1.0 2.0 4.0 8.0; do
    saffron screen \
      bundle_path=<your_trained_detector_bundle.pkl> \
      activations_path=outputs/steering/sweep/alpha${alpha}/activ
  ations/activations.h5 \
      out_dir=outputs/steering/sweep/alpha${alpha}/screen
  done

  Step 5 — Extract structural metrics

  The per-design JSONs already have what you need — no RF3
  folding required:
  import json, glob, pandas as pd

  rows = []
  for path in
  glob.glob("outputs/steering/sweep/*/ablate_*.json"):
      alpha = path.split("/alpha")[1].split("/")[0]
      m = json.load(open(path))["metrics"]
      rows.append({
          "alpha": float(alpha),
          "design_id": path.split("/")[-1].replace(".json",""),
          "max_ca_deviation": m["max_ca_deviation"],
          "n_chainbreaks": m["n_chainbreaks"],
          "helix_fraction": m["helix_fraction"],
          "sheet_fraction": m["sheet_fraction"],
      })
  df = pd.DataFrame(rows)

  ---
  3 plots to make:

  1. Hazard probe score vs α — mean ± std across designs and
  samples. Should go down as α increases. This is the headline
  result.
  2. Structural quality vs α — max_ca_deviation and
  helix_fraction + sheet_fraction (secondary structure content)
  vs α. Shows the tradeoff: at what α does structure start to
  degrade?
  3. Combined tradeoff scatter — x: probe score, y:
  max_ca_deviation, one point per (design, α). α as color. Shows
  the Pareto frontier of safety vs quality.

  The key claim to verify: probe score drops before structure
  degrades. If you can show that α=2 cuts hazard probability by
  ~30% with minimal structural impact, that's a publishable
  result regardless of AUROC.

  Two things to check before running the sweep: (1) does the
  null_block12_f639.json config actually disable steering
  (coeff=0 or steering block absent), and (2) do you have a
  trained detector bundle saved somewhere to pass to saffron
  screen?