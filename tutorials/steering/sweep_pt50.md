# Steering sweep — partial_t=50

Partial diffusion with 50Å noise gives enough denoising steps for steering to
accumulate an effect and for sequences to diverge from the input, making
DTVF scores meaningful. Null + two steered conditions = three-point dose-response.

Outputs go to `outputs/steering/sweep_pt50/` (separate from the pt=5 sweep).

## Commands

```bash
# 1. Null baseline — no steering, partial_t=50
saffron collect model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10_pt50.json \
  hooks=rfd3_partial \
  out_dir=outputs/steering/sweep_pt50/null

# 2. Raw diff-of-means subtraction, coeff=-4
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10_pt50.json \
  hooks=rfd3_partial \
  steering=rawdiff_neg_block12_c4 \
  out_dir=outputs/steering/sweep_pt50/rawdiff_c4

# 3. Raw diff-of-means subtraction, coeff=-8
saffron steer model=rfd3 \
  inputs=tutorials/steering/configs/hazard_10_pt50.json \
  hooks=rfd3_partial \
  steering=rawdiff_neg_block12_c8 \
  out_dir=outputs/steering/sweep_pt50/rawdiff_c8
```

## After runs complete

Extract sequences and score with DTVF:

```bash
python tutorials/steering/extract_sequences.py \
  --sweep_dir outputs/steering/sweep_pt50 \
  --out_fasta outputs/steering/sweep_pt50/sequences.fasta

python tutorials/steering/embed_prot_t5.py \
  --fasta  outputs/steering/sweep_pt50/sequences.fasta \
  --out_h5 outputs/steering/sweep_pt50/embeddings.h5

python tutorials/steering/score_dtvf.py \
  --embeddings outputs/steering/sweep_pt50/embeddings.h5 \
  --model_path DTVF/best_model.pth \
  --out_csv    outputs/steering/sweep_pt50/dtvf_scores.csv
```

Expected output: DTVF virulence probability should decrease from null → c4 → c8
if steering is working. Plot with plot_results.py pointing at sweep_pt50.
