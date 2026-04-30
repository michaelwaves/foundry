# Paper Sweeps

## C4 — Steering generation sweep

Ablate SAE feature 639 (top hazard feature, block12) from 10 hazard inputs at
increasing α. Score steered outputs with DTVF. No activation collection needed.

### Inputs
`tutorials/steering/configs/hazard_10.json` — 10 hazard designs from SafeProtein.

### Commands

```bash
source .venv/bin/activate

# null baseline (no steering)
saffron collect model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10.json \
  hooks=rfd3_partial \
  out_dir=outputs/steering/sweep/alpha0

# alpha = 1
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10.json \
  hooks=rfd3_partial \
  steering=ablate_block12_f639 \
  out_dir=outputs/steering/sweep/alpha1

# alpha = 2
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10.json \
  hooks=rfd3_partial \
  steering=ablate_block12_f639_alpha2 \
  out_dir=outputs/steering/sweep/alpha2

# alpha = 4
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10.json \
  hooks=rfd3_partial \
  steering=ablate_block12_f639_alpha4 \
  out_dir=outputs/steering/sweep/alpha4

# alpha = 8
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10.json \
  hooks=rfd3_partial \
  steering=ablate_block12_f639_alpha8 \
  out_dir=outputs/steering/sweep/alpha8
```

### Outputs
Each run: 10 designs × 8 samples = 80 CIFs + sidecar JSONs with structural metrics.
```
outputs/steering/sweep/
  alpha0/    # baseline
  alpha1/
  alpha2/
  alpha4/
  alpha8/
```

### Evaluation
1. Extract sequences from steered CIFs
2. Score with DTVF — compare virulence probability vs alpha
3. Parse sidecar JSONs for structural quality metrics

### Plots
- DTVF virulence score vs alpha (mean ± std across 10 designs × 8 samples)
- Structural quality vs alpha: `max_ca_deviation`, `helix_fraction + sheet_fraction`
- Tradeoff scatter: DTVF score (x) vs `max_ca_deviation` (y), alpha as color

### Key claim to verify
DTVF score drops before structure degrades. If alpha=2 cuts virulence probability
meaningfully with minimal structural impact, that is the headline result.
