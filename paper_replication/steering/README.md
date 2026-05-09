# Steering

Hooks and steering directions are Hydra config groups under
`sae/src/sae/configs/{hooks,steering}/`. Pass them as overrides alongside
`inputs=<json>`. The inputs JSON contains only per-design entries — no
`run_config` block.

```bash
# Recipe A — single-feature SAE steer (no precompute step needed)
saffron steer model=rfd3 \
  hooks=rfd3_partial \
  steering=sae_block12_f639 \
  inputs=tutorials/steering/configs/steer_block12_f639.json \
  out_dir=outputs/steering/runs/benign_inputs_f639_alpha5

# Recipe B — raw-diff steer (compute first, then apply)
saffron compute_steering_vector \
  inputs=tutorials/steering/configs/diff_haz_minus_ben.yaml \
  out_dir=outputs/steering/vectors/haz_minus_ben

saffron steer model=rfd3 \
  hooks=rfd3_partial \
  steering=raw_diff_block12 \
  inputs=tutorials/steering/configs/steer_diff_block12.json \
  out_dir=outputs/steering/runs/benign_inputs_diff_alpha3

# Recipe C — ablate the hazard direction on hazard inputs
saffron steer model=rfd3 \
  hooks=rfd3_partial \
  steering=ablate_block12_f639 \
  inputs=tutorials/steering/configs/ablate_block12_f639.json \
  out_dir=outputs/steering/runs/hazard_inputs_ablate_f639

# Null-steer regression check (alpha=0 must reproduce saffron collect bit-for-bit)
saffron steer model=rfd3 \
  hooks=rfd3_partial \
  steering=null_block12_f639 \
  inputs=tutorials/steering/configs/null_block12_f639.json \
  out_dir=outputs/steering/runs/null_check
```


## Vaxigen!
     abels_for_steering.csv

● Good. Here's the corrected workflow — all three commands should now work:

  # Step 1 — collect RFD3 activations (partial noising on 59 structures)
  saffron collect model=rfd3 \
    inputs=data_pipelines/vaxijen/rfd3_inputs_all.json \
    out_dir=outputs/vaxijen/collect_all

  # Step 2 — compute pos-minus-neg steering vector across block6/8/12
  saffron compute_steering_vector \
    inputs=tutorials/steering/configs/vaxijen/diff_pos_minus_neg.yaml \
    out_dir=outputs/vaxijen/steering_vectors/pos_minus_neg

  # Step 3 — steer a new design run with block12 vector (coeff=3)
  # Add your test inputs as per-design entries in steer_block12_alpha3.json
  # alongside the existing run_config, then:
  saffron steer model=rfd3 \
    inputs=tutorials/steering/configs/vaxijen/steer_block12_alpha3.json \
    out_dir=outputs/vaxijen/steer_block12_alpha3

  Two things to note:
  - 65 positives are dropped (viral proteins with no PDB) — 28 pos + 31 neg = 59
  examples for vector training. That's slightly imbalanced but workable;
  compute_steering_vector just computes per-class means so unequal counts are
  fine.
  - Step 3 test inputs: add your target PDB entries to steer_block12_alpha3.json
  in the same {"design_key": {"input": "...", "partial_t": 5.0}} format alongside
   the run_config.
