# Steering

```bash
# Recipe A — single-feature SAE steer (no precompute step needed)
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/steer_block12_f639.json \
  out_dir=outputs/steering/runs/benign_inputs_f639_alpha5

# Recipe B — raw-diff steer (compute first, then apply)
saffron compute_steering_vector \
  inputs=tutorials/steering/configs/diff_haz_minus_ben.yaml \
  out_dir=outputs/steering/vectors/haz_minus_ben

saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/steer_diff_block12.json \
  out_dir=outputs/steering/runs/benign_inputs_diff_alpha3

# Recipe C — ablate the hazard direction on hazard inputs
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/ablate_block12_f639.json \
  out_dir=outputs/steering/runs/hazard_inputs_ablate_f639

# Null-steer regression check (alpha=0 must reproduce saffron collect bit-for-bit)
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/steer_block12_f639.json \
  out_dir=outputs/steering/runs/null_check \
  +run_config.steering.block12.0.alpha=0
```
