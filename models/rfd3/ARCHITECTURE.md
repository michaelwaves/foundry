# RFD3 Architecture

## What `rfd3 design` runs

`rfd3 design inputs <job>.json` runs the same RFD3 model regardless of task (monomer design, motif scaffolding, protein–nucleic acid binding, etc.). Task differences live entirely in the **features fed into `TokenInitializer`** — the model graph below never changes.

For the protein–DNA tutorial (`tutorials/rfd3_na_tutorial/rfd3_na_tutorial_activations.json`), the JSON has two parts:

- **`run_config`** — infrastructure (batch count, activation-capture hooks). Hooks attach to submodules by path (e.g. `token_initializer.process_s_trunk`, `diffusion_module.diffusion_transformer.blocks.12.transition_block`) and dump tensors during the run. Introspection only; does not change the model.
- **`dsDNA_complex`** — the design task: protein–DNA complex from `2r5z.pdb`, a contig specifying which regions are fixed vs. designed, per-residue fixed-atom masks, origin tokens, and `is_non_loopy` (rigid-backbone hint).

## Diagram

```mermaid
flowchart TD
    subgraph INPUT["Input features (task-specific)"]
        F["f: tokens, atoms, motif mask,<br/>hotspots, donor/acceptor flags,<br/>ref coords, contig, ori_token..."]
    end

    F --> TI

    subgraph TI["TokenInitializer — 'lightweight trunk'"]
        direction TB
        A1["atom_1d_embedder + token_1d_embedder"]
        A2["RelativePositionEncoding x2<br/>(init pair Z)"]
        A3["sinusoidal motif_pos_embedder<br/>+ ref_pos_embedder"]
        A4["LocalAtomTransformer<br/>(optional, seq-local atom attn)"]
        A5["PairformerBlock x n<br/>(mix single S_I ↔ pair Z_II)"]
        A1 --> A2 --> A3 --> A4 --> A5
    end

    TI --> REPR["{S_I, Z_II, C_L, P_LL, Q_L_init}<br/>single/pair/atom reprs"]

    REPR --> MODE{Training or<br/>Inference?}

    MODE -->|training| DM
    MODE -->|inference| SAMP

    subgraph SAMP["ConditionalDiffusionSampler (EDM, ~200 steps)"]
        direction TB
        S1["Noise schedule<br/>sigma_data=16"]
        S2["For t in timesteps:<br/>call DiffusionModule<br/>optional CFG guidance<br/>motif realignment"]
        S3["Recycle x n_recycle=2"]
        S1 --> S2 --> S3
    end

    SAMP -->|each step, noisy X| DM

    subgraph DM["RFD3DiffusionModule — AF3-style denoiser"]
        direction TB
        D0["scale_positions_in(X_noisy, t) → R_L"]
        D1["FourierEmbedding(t) →<br/>atom time C_L, token time S_I"]
        D2["Atom Attention Encoder<br/>LocalAtomTransformer<br/>(upcast atoms → tokens)"]
        D3["DiffusionTokenEncoder<br/>distogram (65 bins) +<br/>self-conditioning +<br/>PairformerBlock x 2"]
        D4["Diffusion Transformer<br/>18 blocks:<br/>LocalAttentionPairBias +<br/>Transition (FFN)"]
        D5["Atom Attention Decoder<br/>CompactStreamingDecoder<br/>(downcast tokens → atoms)"]
        D6["to_r_update: Q_L → ΔR<br/>scale_positions_out →<br/>X_denoised"]
        D0 --> D1 --> D2 --> D3 --> D4 --> D5 --> D6
    end

    DM -->|predicted X| OUT["Final coords [L, 3]"]

    subgraph HOOKS["Activation capture (from JSON run_config)"]
        H1["hook @ token_initializer.process_s_trunk<br/>(static — once per forward)"]
        H2["hook @ diffusion_module.diffusion_transformer<br/>.blocks.12.transition_block<br/>(dynamic — every 20 sampler steps)"]
    end

    A5 -.captured by.-> H1
    D4 -.captured by.-> H2

    classDef capture fill:#fef3c7,stroke:#a16207
    class HOOKS,H1,H2 capture
    classDef repr fill:#dbeafe,stroke:#1e40af
    class REPR,F repr
```

## Component reference

### `RFD3` (`src/rfd3/model/RFD3.py`)
Outer `nn.Module`. Holds three submodules:
- `token_initializer` — `TokenInitializer`
- `diffusion_module` — `RFD3DiffusionModule` (instantiated via `hydra.utils.instantiate` so shared channel dims `c_s, c_z, c_atom, c_atompair` flow in from the parent)
- `inference_sampler` — `ConditionalDiffusionSampler`

Forward path:
- **Training**: `input["f"]` → `TokenInitializer` → `RFD3DiffusionModule` → denoised coords `[D, L, 3]`
- **Inference**: sampler loops the diffusion module over an EDM noise schedule with optional classifier-free guidance and recycling

### `TokenInitializer` (`src/rfd3/model/layers/encoders.py`)
Lightweight stand-in for AF3's trunk — no MSA module, no templates. Produces:

| Output | Shape | Meaning |
|---|---|---|
| `Q_L_init` | `[L, c_atom]` | atom features |
| `C_L` | `[L, c_atom]` | atom 1D features |
| `P_LL` | `[L, L, c_atompair]` | pairwise atom features |
| `S_I` | `[I, c_s]` | token single |
| `Z_II` | `[I, I, c_z]` | token pair |

Internal stack: 1D embedders → relative-position encodings → optional `LocalAtomTransformer` → `PairformerBlock × n` (mixes single ↔ pair).

### `RFD3DiffusionModule` (`src/rfd3/model/RFD3_diffusion_module.py`)
AF3-style diffusion denoiser. One forward:

1. `scale_positions_in(X_noisy, t)` — scale noisy coords into prediction space `R_L`
2. `FourierEmbedding(t)` → atom time cond `C_L`, token time cond `S_I`
3. **Atom Attention Encoder** — `LocalAtomTransformer` upcasting atoms → tokens
4. **DiffusionTokenEncoder** — distogram (65 bins) + self-conditioning + `PairformerBlock × 2`
5. **Diffusion Transformer** — 18 blocks (`n_block: 18`), each `LocalAttentionPairBias` + transition FFN
6. **Atom Attention Decoder** — `CompactStreamingDecoder` downcasting tokens → atoms
7. `to_r_update` → ΔR, then `scale_positions_out` → `X_denoised`

Default `n_recycle = 2`.

### `ConditionalDiffusionSampler` (`src/rfd3/model/inference_sampler.py`)
Orchestrates inference. EDM-style schedule (default ~200 steps, `sigma_data=16`). Per step: call diffusion module, update noisy coords, optionally apply classifier-free guidance and motif realignment.

## Task differences — where they enter

Everything task-specific enters via the feature dict consumed by `TokenInitializer`. From `configs/model/components/rfd3_net.yaml`:

- `token_1d_features` — `ref_motif_token_type`, `restype`, `ref_plddt`, `is_non_loopy`
- `atom_1d_features` — `ref_atom_name_chars`, `ref_element`, `ref_charge`, `ref_mask`, `ref_is_motif_atom_with_fixed_coord`, `ref_is_motif_atom_unindexed`, `has_zero_occupancy`, `ref_pos`, plus guided features: `ref_atomwise_rasa`, `active_donor`, `active_acceptor`, `is_atom_level_hotspot`

Protein–NA binding uses the donor/acceptor and hotspot channels; motif scaffolding uses the fixed-atom / unindexed channels; monomer design uses neither. The graph is unchanged.

## CLI entry point

`rfd3 design` is registered in the root `pyproject.toml` (`rfd3 = "rfd3.cli:app"`) and defined in `src/rfd3/cli.py`. It is a Typer app that accepts arbitrary Hydra overrides and dispatches to `run_inference(cfg)`.
