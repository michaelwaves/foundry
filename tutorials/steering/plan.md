# Plan — Activation steering during RFD3/RF3 inference

Persona vectors reference: `~/repos/persona_vectors`.

## Goal

Steer the diffusion process by editing residual-stream activations as they pass
through chosen blocks during inference. Two modes, one callsite:

- **SAE-feature mode** — pick top-k AUROC features (e.g. RFD3 block12 #639,
  the hazard-correlated PLA2 feature) and add `alpha · W_dec[feature_id]` to
  the residual at that hook. Cheap — no online SAE forward pass needed.
- **Raw-diff mode** — Persona-Vectors style. Compute
  `mean(positive_activations) − mean(negative_activations)` per hook, save it
  as a `.pt`, add `coeff · diff` to the residual at inference.

Both reduce to the same operation: **add a fixed direction to the hook's
output**. Same callsite, different vector source. The infrastructure is one
implementation; the two modes are config flavors.

CLI surface mirrors `saffron collect`:

```bash
saffron compute_steering_vector inputs=tutorials/steering/configs/diff_haz_minus_ben.yaml out_dir=...
saffron steer                  inputs=tutorials/steering/configs/steer_block12_f639.json   out_dir=...
```

---

## Reuse, don't rebuild

Three components already exist and we extend them in-place:

| Existing | Where | Change |
|---|---|---|
| Forward-hook lifecycle (`register`, `on_design_start`, `close`) | `sae/src/sae/activation_buffer.py:41-71` | Hook closure also adds an optional steering tensor; otherwise unchanged |
| RFD3 + RF3 collector engines | `models/rfd3/.../engine.py:295-315`, `models/rf3/.../inference_engines/rf3.py:384-402` | Pass through a steering registry alongside the activation buffer; no API change at the engine level |
| Inputs JSON schema seeding | `tutorials/sae_data_*/build_inputs.py:_load_or_seed_run_config` | Allow a `steering` block alongside `activation_collection` |
| SAE encode/decode | `sae/src/sae/models/matryoshka_batch_topk.py` | Use `sae.W_dec` directly to derive feature direction vectors offline |

The clean equivalence is what makes this small: `out_steered = out + Σᵢ vᵢ`,
where each `v` is a per-hook fixed tensor of shape `(activation_dim,)`. SAE
features and raw-diff vectors are two ways to compute `v`.

---

## Two phases, two CLIs

### Phase 1 — compute the direction vector (offline, one-time)

**Raw-diff mode:** new `saffron compute_steering_vector` reads two
collected activation h5s, applies the same per-token mean we already use in
the SAE training loader, computes `mean(pos) - mean(neg)` per hook, writes one
`.pt` per hook.

```yaml
# diff_haz_minus_ben.yaml
positives_h5: outputs/.../hazard_acts/activations.h5
negatives_h5: outputs/.../uniprot_benign_acts/activations.h5
hooks: [block6, block8, block12]
normalize: unit          # unit | none — recommend unit so coeff is interpretable
```

Output:
```
out_dir/
  block6.pt   # tensor (activation_dim,)
  block8.pt
  block12.pt
  meta.json   # n_pos, n_neg, hook layout, normalize mode
```

**SAE-feature mode:** no new CLI. The "vector" is just `alpha · sae.W_dec[feature_id]`,
loaded on demand from the SAE checkpoint at inference time. Avoids
disk-writing and lets users iterate `(feature_id, alpha)` from
`top_features.parquet` without re-running anything.

### Phase 2 — steer at inference

```bash
saffron steer model=rfd3 inputs=tutorials/steering/configs/steer_block12_f639.json out_dir=outputs/steering/runs/f639_alpha5/
```

The engine path is identical to `saffron collect` — same Hydra configs, same
RFD3 inference loop. Only difference: the activation hooks return modified
tensors instead of just observing.

---

## Inputs JSON — additive extension

Existing keys (`run_config.activation_collection.hooks`, per-design entries)
unchanged. Add one new sibling:

```json
{
  "run_config": {
    "activation_collection": {"hooks": [...]},
    "steering": {
      "block12": [
        {
          "mode": "sae_feature",
          "sae_path": "outputs/sae/2026-04-26_15-38-55/train/block12/final.pt",
          "feature_id": 639,
          "alpha": 5.0,
          "apply_at_steps": "all"
        },
        {
          "mode": "raw_diff",
          "vector_path": "outputs/steering/vectors/haz_minus_ben/block12.pt",
          "coeff": 3.0,
          "type": "steer"
        }
      ],
      "block8": [...]
    }
  },
  "design_001": {"input": "...", "partial_t": 5.0}
}
```

Per-hook list, so multiple steers compose by addition (the cleanest semantics
and what persona_vectors does for multi-vector). Each entry has:

| key | meaning |
|---|---|
| `mode` | `sae_feature` or `raw_diff` |
| `feature_id`, `alpha` | sae_feature only — which dictionary feature, by how much |
| `sae_path` | sae_feature only — checkpoint to read `W_dec` from |
| `vector_path` | raw_diff only — the `.pt` from compute_steering_vector |
| `coeff` | raw_diff only — magnitude on the unit vector |
| `type` | `steer` (add) or `ablate` (project out — `out − (out·v̂) v̂`) |
| `apply_at_steps` | `"all"` \| `[10, 20]` \| `{"start": 50}` — which diffusion steps fire steering |
| `apply_to_tokens` | optional mask spec — default `"all"`. Reserved for per-residue ablation later. |

Steering hooks are **independent of collection hooks** — the same block can
have a steering entry without being collected, or both. We register a hook on
each unique `module_path` once and let it dispatch to (steer + collect)
callbacks.

---

## File layout

```
sae/src/sae/
  steering/
    __init__.py
    config.py             # SteeringSpec dataclass, parse from inputs.json
    vectors.py            # load .pt, slice sae.W_dec, normalize, cache
    hooks.py              # build_steering_hook() — closure fed to register_forward_hook
    compose.py            # combine multiple SteeringSpecs into one direction per (hook, step)
    compute_diff.py       # offline mean-diff computation (used by compute_steering_vector CLI)
  cli.py                  # add `compute_steering_vector` and `steer` commands
  activation_buffer.py    # one new line: call steering callback before collection logic

models/rfd3/.../engine.py # one new line: pass steering registry to ActivationBuffer
models/rf3/.../inference_engines/rf3.py  # same one-line change

tutorials/steering/
  plan.md                 # this file
  configs/
    diff_haz_minus_ben.yaml
    steer_block12_f639.json
    steer_diff_block12.json
    ablate_block12_f639.json
  README.md               # bash commands only, mirrors tutorials/classifiers/README.md
```

One class per file, files <150 lines per the global guidelines. The hook
implementation itself is ~30 lines.

---

## The hook splice point

Inside `ActivationBuffer.register()` (`sae/src/sae/activation_buffer.py:53`):

```python
def hook(m, inp, out):
    # NEW — apply steering BEFORE collection so we measure the steered activation
    if cfg.name in self._steering_directions:
        direction, kind = self._steering_directions[cfg.name](self._step_counts[cfg.name])
        if direction is not None:
            if kind == "add":
                out = out + direction.to(device=out.device, dtype=out.dtype)
            elif kind == "ablate":
                v = direction.to(device=out.device, dtype=out.dtype)
                out = out - (out @ v).unsqueeze(-1) * v / (v.dot(v) + 1e-12)

    # existing collection logic — unchanged
    count = self._step_counts[cfg.name]
    ...
    return out
```

Five constraints, all met by this design:

1. **Same shape, dtype, device as `out`** — direction is `(activation_dim,)`,
   broadcast over `(B, L, C)` adds to every token in every batch position.
2. **No grad context** — inference is `torch.no_grad()`; we don't need
   backward; no `requires_grad=True` anywhere.
3. **Step-aware** — closure receives current step count to gate by
   `apply_at_steps`.
4. **Token-aware (future)** — extend the closure to take token mask later;
   default broadcasts to all tokens.
5. **Dispatch returns the modified output** — PyTorch forward hooks accept
   the return value as the new layer output.

---

## Composing multiple steers per hook

When a hook has multiple `steering` entries, they're additive at the
(direction × coefficient) level:

```
v_total = Σᵢ coeffᵢ · normalize(directionᵢ)   # for steer entries
out     = out + v_total                         # then add once
```

Ablate is non-commutative with steer; if both are present at the same hook,
ablate first (project out), then add steer. This matches what
persona_vectors does in the multi-steer training-time path.

---

## Why two modes share the same callsite

The math collapses both modes to "add a constant tensor per hook":

- **SAE feature**: `delta = alpha · W_dec[feature_id]` (a row of the
  decoder, shape `(activation_dim,)`). Computed once at config load,
  reused every step.
- **Raw diff**: `delta = coeff · (mean_pos − mean_neg)` (also
  `(activation_dim,)`). Computed offline by `compute_steering_vector`,
  loaded from `.pt` at config load.

Both vectors live in the same residual-stream space — that's the whole
point of "the SAE decoder maps features back into the residual stream."
This is deliberate: it lets us A/B test "which is the better lever — a
single interpretable feature, or the full mean-diff direction?" with the
same plumbing.

---

## Implementation phases

1. **Extend HookConfig + ActivationBuffer** to accept an optional
   per-hook `steering_callback(step) -> (direction, kind) | (None, None)`.
   Register the callback alongside the collection closure. ~25 LOC + tests.

2. **`steering/vectors.py`** — load `.pt` files, slice
   `sae.W_dec[feature_id]` for SAE features, normalize. Pure compute,
   easy to unit test. ~50 LOC.

3. **`steering/compose.py`** — given a list of `SteeringSpec` per hook,
   return a step-aware callback that composes additive directions and
   optional ablation. ~40 LOC.

4. **`compute_steering_vector` CLI** — read positive and negative
   activations h5, compute mean-diff per hook, write `.pt`. Mirrors the
   pattern in `sae/src/sae/dataset.py`. ~80 LOC.

5. **`steer` CLI** — Hydra-driven, dispatches to the existing collector
   engine but with steering directions wired into the activation buffer.
   The diff vs `saffron collect` is one extra parameter through the
   engine. ~40 LOC.

6. **Engine wire-up** — RFD3 + RF3 each take one line: pass
   `steering_directions` from inputs.json into `ActivationBuffer(...)`.

7. **Validation hooks** — for each `saffron steer` run, also collect the
   target hook activations (steering + collection coexist) and write a
   `steering_report.json`:
   - `projection`: mean of `(steered_act @ direction) / |direction|`
     across tokens — should be larger than the same metric on an
     unsteered run.
   - `cosine_similarity` between mean activation and direction.
   Mirrors `persona_vectors/eval/cal_projection.py`.

8. **Structure-level eval** — write a small script that runs the same
   inputs twice (with and without steering), computes per-design RMSD
   between the generated structures, and tabulates which designs
   structurally diverged most. Lives in `tutorials/steering/`.

---

## Sanity checks before believing any result

- **Null steering returns the unsteered run.** Set every coeff/alpha
  to 0 and confirm cif outputs are bit-identical to a regular
  `saffron collect`. Catches accidental in-place edits.
- **Steering direction is on the right device/dtype.** Add a unit test
  that runs the hook on a fake module, asserts no device mismatch.
- **Projection metric goes up** when we steer along a vector and **down**
  when we ablate it. If not, the sign convention or normalization is wrong.
- **Per-step gating works.** Set `apply_at_steps: [50]` and verify the
  collected activations show the spike only at step 50.

---

## Recipes — what to actually run

### Recipe A — single-feature SAE steer along the top hazard direction

Take RFD3 block12 #639 (corrected sweep top: AUROC 0.815, hazard-firing,
fires on PLA2 catalytic residues of UniProt P00626). Steer benign UniProt
inputs along that direction at varying alpha, render generated structures.

```bash
saffron steer model=rfd3 inputs=tutorials/steering/configs/steer_block12_f639.json out_dir=outputs/steering/runs/benign_inputs_f639_alpha5/
```

Question: does steering benign inputs along a hazard-firing feature produce
structures that look more PLA2-like (cysteine clustering, calcium-binding loop
geometry)?

### Recipe B — raw-diff steer

Compute `mean(SafeProtein hazards) − mean(UniProt benigns)` per hook,
steer benign inputs along it, compare to single-feature steer.

```bash
saffron compute_steering_vector inputs=tutorials/steering/configs/diff_haz_minus_ben.yaml out_dir=outputs/steering/vectors/haz_minus_ben/
saffron steer                  inputs=tutorials/steering/configs/steer_diff_block12.json   out_dir=outputs/steering/runs/benign_inputs_diff_alpha3/
```

Question: is the dense mean-diff direction more or less effective than the
sparse single-feature direction at producing hazard-like structures?

### Recipe C — ablate

Steer hazardous inputs *against* the hazard direction (ablate or steer with
negative coeff). Does RFD3 produce structures that lose hazardous features?
This is the safety-relevant direction.

```bash
saffron steer model=rfd3 inputs=tutorials/steering/configs/ablate_block12_f639.json out_dir=outputs/steering/runs/hazard_inputs_ablate_f639/
```

---

## Open design questions

1. **Step gating across recycles (RF3)**. RF3's hooks fire ~500 times per
   design across recycles + diffusion steps. `apply_at_steps: "all"` is fine
   but cumulative; per-recycle vs per-step semantics needs a clean
   abstraction. Recommend: integer step counts, with a helper `every_n` and
   `range` syntax in the JSON.

2. **Token-level steering**. The hook sees `(B, L, C)` — adding a single
   `(C,)` direction broadcasts to every token. For per-residue steering
   ("only edit hydrophobic residues"), we'd need a token mask passed through
   the hook. Defer — start with the default broadcast and add later.

3. **SAE-feature steer at multiple scales**. Matryoshka SAEs have nested
   group sizes. A feature in group 0 (smallest dict) means something different
   from one in group 4. Should the steering API surface group selection?
   Probably not at v1 — just use the global feature_id and document.

4. **Magnitude calibration**. Persona vectors use coeffs in [1, 5]; our SAE
   features have raw activations up to ~225 (per the visualizer smoke test).
   Need a normalization convention so `coeff=1` is meaningful. Recommend:
   normalize the direction to unit length, surface coeff in
   "standard deviations of the layer's activation norm".

5. **What to save per run**. The collector engine already saves cif.gz +
   json metadata per design. For steering runs, also save:
   - `steering_config.json` (the resolved spec, dereferenced from the inputs)
   - `direction_vectors.pt` (the actual tensors used, cached for repro)
   - `steered_activations.h5` (if collection hooks are also configured)
   - `steering_report.json` (projection metrics, the validation step above)
