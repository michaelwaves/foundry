# Plan — SAE/saffron refactor: Hydra-native hooks, steering, and inference datasets

## TL;DR

The codebase is **already 80% there**. `rf3/configs/inference_engine/rf3.yaml`
has first-class `activation_collection` and `steering` slots. `rf3 fold` and
`saffron collect` consume the same JSON shape. The collector layer is Typer
on the outside but Hydra on the inside.

What's chafing is the seam between Hydra and JSON: hooks live in floating
YAMLs (`data_pipelines/hooks/*.yaml`), steering specs live embedded in
`inputs.json` under a `run_config` key that the collector then unpacks back
out into a sidecar `__examples.json`. `build_inputs.py` is glue code whose
sole job is to concatenate (sources CSV) + (hooks YAML) → one JSON, which
the collector immediately re-splits.

The clean refactor: **`inputs.json` keeps its job — the per-design list to
fold — and nothing else. Hooks and steering become Hydra config groups
passed as overrides** (`saffron collect inputs=... hooks=rf3_default
steering=none`). Hooks and steering are orthogonal to which proteins you're
folding; they shouldn't be inlined into the design list.

`data_pipelines/` stays largely as-is — it does genuine data-prep work
(download, length filter, PDB validation, class balancing) that is not
Hydra-expressible. `build_inputs.py` shrinks to a CSV→designs renderer
(no more hooks concat).

A minimal version (Option 1) gets the headline win in ~1 day.
A medium version (Option 2) adds an optional `dataset=<group>` Hydra
override as an alternative to `inputs=<json>` for users who don't want to
materialize a JSON.

---

## How foundry is architected today

### Three layers, each with its own config style

```
┌─────────────────────────────────────────────────────────────┐
│  saffron CLI                          Typer (top level)     │
│    saffron collect / steer / compute_steering_vector        │
│    → dispatches to model collector with `model=<name>`      │
└──────────────────────┬──────────────────────────────────────┘
                       │ raw CLI overrides + inputs.json path
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Model collectors                     Hydra (compose)       │
│    sae/src/sae/collectors/{rf3,rfd3}.py                     │
│    - Compose the model's inference Hydra config             │
│    - Optionally apply hooks=<yaml> overlay                  │
│    - Optionally apply embedded run_config from inputs.json  │
│    - Splits inputs.json into sidecar __examples.json        │
└──────────────────────┬──────────────────────────────────────┘
                       │ DictConfig + path to examples JSON
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Model engines                        Hydra (consume)       │
│    rf3.inference_engines.rf3.RF3InferenceEngine             │
│    rfd3.engine.RFD3InferenceEngine                          │
│    Already accept activation_collection / steering kwargs   │
│    via cfg.activation_collection, cfg.steering              │
└─────────────────────────────────────────────────────────────┘
```

The engine layer is fully Hydra-native. It already has these slots:

```yaml
# models/rf3/configs/inference_engine/rf3.yaml:35-41
activation_collection: null
steering: null
```

with a comment explicitly saying "populated at runtime by the rf3 collector
from the embedded run_config in the inputs JSON, or via `hooks=...`".

### The data prep layer

`data_pipelines/` is imperative scripts (download shells + Click CLIs):

```
download_<name>.sh        →  raw FASTAs
fasta_to_sources          →  sources.csv  (SourceRow schema)
build_inputs              →  inputs.json  (sources.csv + hooks.yaml concat)
[rf3 fold + attach_pdbs]  →  PDB structures attached for RFD3
[filter_pdbs]             →  RFD3-compatible + class-balanced
```

`SourceRow` (`data_pipelines/sources.py:14`) is a 6-column schema
(`name, label, sequence, structure_path, n_residues, min_residue`). Every
step reads/writes this — it's the universal exchange format.

`build_inputs.py` is the concatenator: it reads a sources.csv plus a hooks
YAML and emits an inputs.json shaped like:

```json
{
  "run_config": {"activation_collection": {"hooks": [...]}},
  "design_001": {"input": "...", "partial_t": 5.0},
  "design_002": {...}
}
```

### Where the JSON gets unpacked again

`sae/src/sae/collectors/rf3.py` reverses what `build_inputs.py` did:

```
inputs.json ──┐
              ├──→  __examples.json   (just the per-design entries)
              └──→  cfg.activation_collection, cfg.steering   (Hydra overlay)
```

This is the smell: `build_inputs` concatenates, the collector pulls apart.
The two halves never need to be one file. They were merged for one reason —
**`rf3 fold` reads the same inputs.json shape**, so a single file lets us
fold and collect with the same config. That coupling is real but doesn't
require the merger to happen at `build_inputs` time.

---

## What's already aligned

| Piece | Status |
|---|---|
| Engine accepts `activation_collection` + `steering` as kwargs | ✅ both rf3 and rfd3 |
| Engine config has Hydra slots for both | ✅ `inference_engine/rf3.yaml` |
| `rf3 fold` and `saffron collect` consume same input JSON | ✅ documented in `data_pipelines/README.md` |
| Collector composes Hydra inference config | ✅ `_config_dir()` resolves model package's configs |
| Steering spec schema (mode, alpha, feature_id, sae_path) | ✅ `sae/steering/config.py` |
| Per-hook list semantics for steering composition | ✅ `compose.build_callbacks()` |

All of the above means the Hydra plumbing for hooks/steering exists end to
end. The gap is purely at the front door.

## What's chafing

| Smell | Where | Why it bites |
|---|---|---|
| Hooks YAMLs float outside the Hydra tree | `data_pipelines/hooks/*.yaml` | Can't be referenced by Hydra group syntax (`hooks=rf3_default`); duplicated as paths in scripts |
| Steering JSONs float outside the Hydra tree | `tutorials/steering/configs/*.json` | Each new experiment = a hand-rolled JSON; can't compose mode + layer + alpha as separate groups |
| `inputs.json` mixes 3 concerns | run_config + per-example data + (some) global args | `build_inputs` joins, collector splits, sidecar `__examples.json` is the workaround |
| `build_inputs.py` is glue with no logic | `data_pipelines/build_inputs.py` | Reads sources, reads hooks YAML, writes JSON. ~150 lines for a `cat` |
| saffron CLI is Typer, models are Hydra | `sae/src/sae/cli.py:17-65` | No `--cfg job` / `--multirun` / config groups at the top level |
| The same dataset is re-rendered per hooks-config | vaxijen has 1 sources CSV → must rebuild inputs JSON per hooks change | Inputs JSON is a (data × hooks) cross product instead of just data |

---

## Could the data_pipelines stuff be replaced by Hydra dataset configs?

**Mostly no.** The Hydra dataset configs in `models/rfd3/configs/datasets/`
are *training-data* configs — they point at parquet files of full PDB
assemblies, declare augmentation, batch sizing, sampling weights, masking
frequencies. Their purpose is to feed the training loop. They are not a
substitute for an inference-time, curated, label-balanced eval set.

**What actually has to be imperative:**

| Step | Reason it can't be Hydra |
|---|---|
| `download_*.sh` | Network IO, resumable checkpointed downloads |
| `fasta_to_sources` | FASTA parsing, non-canonical residue rejection, length cuts |
| `attach_pdbs` | Filename matching across recursive dir, multi-suffix dispatch |
| `filter_pdbs` | Stratified per-bucket class balancing — algorithmic, not declarative |
| PDB CA validation | `first_missing_ca` walks the file, returns a reason string |

**What could become Hydra config:**

A new config group `sae/configs/datasets/<name>.yaml` could declare:

```yaml
# sae/configs/datasets/vaxijen_positives.yaml
_target_: sae.datasets.SourcesDataset
sources_csv: ${oc.env:FOUNDRY_ROOT}/data_pipelines/vaxijen/sources_positives.csv
label_column: label
prefix: vax_pos
length_filter: {min: 50, max: 300}
```

This replaces `build_inputs.py` for the sources→examples step. The
`SourcesDataset` class is ~30 lines: read CSV, filter, convert to the
list-of-dicts shape that the engine wants. Same idea as a HuggingFace
`Dataset.from_csv()` — declarative pointer at a CSV with a column spec.

**Recommendation:** keep `data_pipelines/` as the imperative prep layer
(download + parse + balance), and add a thin Hydra "inference dataset"
config group that points at its outputs. Don't try to subsume
`data_pipelines/` — it's earning its keep.

---

## Refactor — three options at three sizes

### Option 1 (minimal) — Hooks + steering join the existing pass-through Hydra groups

This isn't a new mechanism — it's making `hooks=` and `steering=` behave
**identically to how `inference_engine=` already works** under saffron.
Today, anything you put on the saffron CLI after `model=<name>` is
forwarded to that model's Hydra compose. So this works *now*:

```bash
saffron collect model=rf3 \
  inference_engine=rf3 \                # already a pass-through Hydra group
  diffusion_batch_size=10 \             # already overrides cfg.diffusion_batch_size
  inputs=data_pipelines/vaxijen/rf3_inputs_positives.json
```

The only reason `hooks=` and `steering=` aren't on this list yet is that
the YAMLs they'd reference don't live in any Hydra-searchable directory.
Move them into a config-search-path that the rf3/rfd3 collectors register,
and the same pass-through mechanism handles them for free:

```
sae/src/sae/configs/             # NEW — added to the Hydra search path by both collectors
  hooks/
    rf3_default.yaml             # was data_pipelines/hooks/rf3.yaml
    rfd3_partial.yaml            # was data_pipelines/hooks/rfd3_partial.yaml
  steering/
    none.yaml                    # null pass-through
    sae_block12_f639.yaml        # was tutorials/steering/configs/steer_block12_f639.json (run_config part)
    raw_diff_block12.yaml
    ablate_block12_f639.yaml
```

After the move, the existing CLI just works:

```bash
saffron collect model=rf3 \
  inference_engine=rf3 \                # existing pass-through
  hooks=rf3_default \                   # new pass-through, same mechanism
  steering=none \                       # new pass-through, same mechanism
  inputs=data_pipelines/vaxijen/rf3_inputs_positives.json
```

The engine already reads `cfg.activation_collection` and `cfg.steering`
(those slots already exist in `inference_engine/rf3.yaml`). The hooks and
steering YAMLs only need to populate those keys — pure Hydra composition,
zero new dispatch logic.

**`build_inputs.py` simplifies**: drop the `--hooks-yaml` argument and the
`run_config` injection. Output is just `{design_001: {...}, design_002: {...}}`.

**`inputs.json` interface is unchanged.** Same shape, same role. The only
thing that disappears is the `run_config` key inside it — which is exactly
the bit that Hydra is now supplying.

**Cost:** ~1 day. New `sae/configs/` dir; one-line addition to each
collector to register that dir on rf3/rfd3's Hydra search path; update
`build_inputs.py` to drop `run_config`.

**Wins:**
- Hooks + steering compose with `inference_engine=`, `model=`, etc. via the
  same mechanism users already know.
- New steering experiment = one new YAML in `sae/configs/steering/`,
  not a hand-edited JSON.
- `inputs.json` becomes pure data and is reusable across every hooks ×
  steering combination without re-rendering.
- Multirun "for free": `saffron collect -m steering=glob(sae_block12*)`.

**Doesn't address:** absolute paths inside steering YAMLs (the
`sae_path: outputs/sae/<timestamp>/...` problem) — that's a separate
registry concern listed in Open Questions.

### Option 2 (medium) — Optional `dataset=<group>` as an alternative input source

On top of Option 1: keep `inputs=<json>` working **exactly as today**, but
add an alternative: a `dataset=<group_name>` Hydra override that points at a
sources.csv (or HF dataset) directly, bypassing the need to render a JSON
first.

```bash
# Today's interface — still works after Option 1, unchanged
saffron collect model=rf3 \
  inputs=data_pipelines/vaxijen/examples.json \
  hooks=rf3_default \
  steering=none

# New alternative: skip the JSON render, point at the dataset directly
saffron collect model=rf3 \
  dataset=vaxijen_positives \
  hooks=rf3_default \
  steering=none
```

`inputs=` and `dataset=` are mutually exclusive — you provide exactly one.
`inputs=` is the explicit list-of-designs path (current behavior, preferred
when you want a single shareable artifact). `dataset=` is the
"materialize-on-the-fly from a registered source" path (preferred for
sweeps where rendering N JSONs would be silly).

```yaml
# sae/configs/dataset/vaxijen_positives.yaml
_target_: sae.datasets.SourcesDataset
sources_csv: ${oc.env:FOUNDRY_ROOT}/data_pipelines/vaxijen/sources_positives.csv
length_filter: {min: 50, max: 300}
```

**Cost:** ~2-3 days on top of Option 1. Touches:
- New `sae.datasets` module (~50 lines: `SourcesDataset` reads CSV → list of
  per-design dicts in the same shape `inputs.json` produces)
- Collector dispatch: if `cfg.dataset` is set, instantiate it; else load
  `cfg.inputs` JSON as today
- New Hydra config group `sae/configs/dataset/`

**Wins:** Sweeps without per-experiment JSON rendering. `saffron collect -m
dataset=glob(vaxijen_*)` runs over both positives and negatives in one
multirun.

**Doesn't change:** `inputs.json` interface, `saffron` CLI shape, anything
about how steering/hooks specs are read. This is purely a new optional input
path alongside the existing one.

### Option 3 (ambitious) — Unify with rf3/rfd3's inference Hydra tree

On top of Option 2: don't have a separate `sae/configs/`. Instead:
- Put `hooks/`, `steering/`, `dataset/inference/` config groups directly
  inside `models/rf3/configs/` and `models/rfd3/configs/`.
- `saffron collect` becomes a thin wrapper that adds a `--collect` flag to
  `rf3 fold` / `rfd3 inference` instead of being a separate Typer app.
- `rf3 fold` already shares the inputs JSON shape; this collapses them.

**Cost:** ~1-2 weeks. Worth it only if rf3/rfd3 maintainers also want
unified inference. Saffron disappears as a separate CLI; it becomes a
config flag on the model's own fold/inference command.

**Wins:** One CLI. One config tree. No "saffron knows about rf3's Hydra"
indirection. Steering/SAE collection becomes a first-class capability of
the inference engine, not a wrapper.

**Risks:** rf3/rfd3 are upstream. Forking their CLI to add saffron
features is a maintenance liability. Probably reject this unless those
projects are willing to upstream the changes.

---

## Recommendation

Do **Option 1** now. It's a 1-day cleanup with clear wins:

- All YAMLs/JSONs that were floating outside the Hydra tree become named
  Hydra config groups (`hooks=rf3_default`, `steering=sae_block12_f639`).
- `inputs.json` keeps its job — list of designs to fold — and nothing else.
- `build_inputs.py` drops to ~50 lines (just sources.csv → examples list).
- The `data_pipelines/hooks/` directory disappears (moved into the saffron
  package).
- `tutorials/steering/configs/*.json` collapse to YAMLs in
  `sae/configs/steering/` plus a much smaller examples JSON per dataset.

Then **revisit Option 2** once Option 1 is in place and you've felt the
remaining pain. The Option-2 win (skip the JSON render for sweep-style
runs) only matters if you're running enough sweeps that pre-rendering is
annoying. After Option 1, decide whether `dataset=<group>` is worth the
extra surface area or whether `inputs=<json>` is fine forever.

**Don't do Option 3** unless rf3/rfd3 upstream wants unified inference.

---

## What stays in `data_pipelines/`

After Option 1 or 2:

| File | Stays? | Why |
|---|---|---|
| `download_*.sh` | ✅ | Network IO, can't be Hydra |
| `fasta_to_sources.py` | ✅ | FASTA parsing + filter, imperative |
| `attach_pdbs.py` | ✅ | Filename glue, imperative |
| `filter_pdbs.py` | ✅ | Stratified balancing, algorithmic |
| `pdb_utils.py` | ✅ | PDB validation primitives |
| `sources.py` (SourceRow) | ✅ | Universal exchange format |
| `push_to_hub.py` | ✅ | HF upload helper |
| `build_inputs.py` | ⚠️ shrinks | Drop run_config concat; just sources.csv → examples list |
| `hooks/*.yaml` | ❌ moves | → `sae/configs/hooks/` |

The data_pipelines layer is doing real work. The refactor reduces it; it
doesn't subsume it.

---

## Open questions

1. **Where do shared steering vectors live?** Today, `vector_path` in a
   steering JSON is an absolute path to `outputs/steering/vectors/.../*.pt`.
   That's fine for one user, hostile to repro. Option: make a steering
   config support a `${oc.env:STEERING_VECTORS_DIR}/<name>` interpolation,
   and ship a small registry yaml.

2. **Does `rf3 fold` need to keep reading the unified `inputs.json`?**
   Currently yes — `data_pipelines/README.md:42-50` documents
   `rf3 fold inputs=foo.json`. After refactor, `build_inputs --emit-rf3-fold`
   could render a dataset config + examples back into a single JSON for
   compatibility. Or: teach `rf3 fold` to also accept a Hydra dataset
   config (Option 3 territory).

3. **Multi-dataset collect runs.** Some sweeps want "collect on (vaxijen
   pos + neg) ∪ vfdb hazards" in one go. Today: pre-merge the sources CSVs.
   With Hydra dataset groups, we could express union via `dataset=[vaxijen_positives, vfdb_hazards]`
   if `SourcesDataset` learns to concatenate. Defer to v2.

4. **HF dataset story.** `build_inputs.py` already supports
   `--hf-dataset NAME`. The refactored `SourcesDataset` should mirror this:
   `_target_: sae.datasets.HFDataset` with `name: baker-lab/foundry-safeprotein`.
   Same shape on the inside, different source.

5. **Steering vector provenance.** When a steering YAML references
   `outputs/sae/<timestamp>/train/block12/final.pt`, that path is
   reproducibility-fragile. Idea: SAE training writes a
   `models/sae_registry.yaml` mapping symbolic names (`block12_v1`) to
   timestamped paths. Steering configs reference symbolic names. Same
   mechanism as model registries in W&B.

---

## File-level diff for Option 1 (the minimal refactor)

**New:**
```
sae/src/sae/configs/
  __init__.py
  hooks/
    rf3_default.yaml             # copied from data_pipelines/hooks/rf3.yaml
    rfd3_partial.yaml            # copied from data_pipelines/hooks/rfd3_partial.yaml
  steering/
    none.yaml                    # {} — for the unsteered baseline
    sae_block12_f639.yaml        # the four tutorial steering configs, run_config only
    raw_diff_block12.yaml
    ablate_block12_f639.yaml
    null_block12_f639.yaml
```

**Modified:**
```
sae/src/sae/collectors/rf3.py    # accept hooks=<group_name> via Hydra search path
sae/src/sae/collectors/rfd3.py   # same
sae/src/sae/cli.py               # docstring updates; help text mentions config groups
data_pipelines/build_inputs.py   # drop --hooks-yaml; drop run_config injection
                                 # output is just `{"design_x": {...}, ...}`
data_pipelines/README.md         # update step 5 to drop --hooks-yaml
tutorials/steering/configs/*.json  # split: keep per-design entries, move
                                   # run_config.{activation_collection,steering}
                                   # to sae/configs/{hooks,steering}/
```

**Deleted:**
```
data_pipelines/hooks/            # moved into the saffron package
```

That's the whole refactor. Net SLOC: probably negative. Net config
discoverability: massively positive.
