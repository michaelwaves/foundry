# RFdiffusion3 — Symmetric Design Tutorial

How to run symmetric protein design with RFdiffusion3 (RFD3). Covers cyclic
(`Cn`) and dihedral (`Dn`) groups — the only two families currently supported.

---

## How symmetry works in RFD3

Symmetry is enabled in two places:

1. **Sampler kind** — pass `inference_sampler.kind=symmetry` on the CLI. This
   swaps the default EDM sampler for the symmetry sampler
   (`models/rfd3/configs/model/samplers/symmetry.yaml`), which symmetrizes the
   noise/structure during the first `sym_step_frac` of the trajectory
   (default 0.9 → 90 %).
2. **Per-design `symmetry` block** — declared in the input JSON/YAML for each
   design key:

   ```json
   "symmetry": {
       "id": "C3",
       "is_symmetric_motif": true,
       "is_unsym_motif": "Y1-11,Z16-25"
   }
   ```

   - `id` — symmetry group: `C2`, `C3`, … (cyclic), `D2`, `D3`, … (dihedral).
   - `is_symmetric_motif` — input motif is already pre-symmetrized around the
     origin. Defaults to `true`; this is currently the only supported mode.
   - `is_unsym_motif` — comma-separated contig / ligand names that should *not*
     be symmetrized (e.g. a single DNA strand, a single bound ligand).

For motif scaffolding, the input PDB **must already be symmetrized about the
origin**. The four PDBs in `inputs/` satisfy this.

### Useful CLI flags for symmetric runs

| Flag                              | Why                                                           |
| --------------------------------- | ------------------------------------------------------------- |
| `inference_sampler.kind=symmetry` | Required — turns on the symmetry sampler.                     |
| `diffusion_batch_size=1`          | Recommended — symmetric runs are memory-heavy.                |
| `low_memory_mode=True`            | Use only if you still OOM (slower).                           |
| `n_batches=N`                     | Total designs = `n_batches × diffusion_batch_size` per spec.  |
| `dump_trajectories=True`          | Save the denoising trajectory.                                |

---

## Files

| File                          | What it designs                                                          |
| ----------------------------- | ------------------------------------------------------------------------ |
| `uncond_cyclic.json`          | Unconditional C5 homo-pentamer, 100 res/subunit.                         |
| `uncond_dihedral.json`        | Unconditional D4 octamer, 50 res/subunit.                                |
| `motif_C2_unindexed.json`     | C2 enzyme active site scaffolding around `ORO,ZN` (PDB 1j79).            |
| `motif_C2_indexed_HEM.json`   | C2 scaffold around a single (unsymmetrized) `HEM` ligand (PDB 1bfr).     |
| `motif_C3_DNA.json`           | C3 protein around a DNA double helix; DNA chains stay unsymmetrized.     |
| `run.sh`                      | Shell script to run all five.                                            |
| `inputs/*.pdb`                | Pre-symmetrized motif PDBs.                                              |

---

## Run

From this directory, with the foundry venv active:

```bash
source ../../.venv/bin/activate
./run.sh
```

Or run a single spec:

```bash
rfd3 design \
  inputs=uncond_cyclic.json \
  out_dir=outputs/uncond_cyclic \
  inference_sampler.kind=symmetry \
  diffusion_batch_size=1 \
  n_batches=2
```

Outputs land in `outputs/<spec>/`. Each output JSON logs the resolved spec and
sampled contig so you can reproduce a single design later.
