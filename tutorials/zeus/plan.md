# ZeUS: Efficient Attention for Symmetric Protein Generation in RFD3

**Goal**: Exploit n-fold symmetry (Cn, Dn) in homomeric protein complexes to reduce the
diffusion transformer's attention cost from O(L²) to O(L²/n), where L = n × M (n chains of M tokens).

---

## Core Insight

For a Cn-symmetric complex, every subunit is a rotated copy of the asymmetric unit (ASU).
After the symmetry-enforcing step in the sampler (`apply_symmetry_to_xyz_atomwise`), the
following hold at every diffusion step:

1. **Single representations** are identical across chains: `A_I[i + kM] = A_I[i]` for k ∈ [1, n).
2. **Pair representations** have block-circulant structure:
   `Z_II[i + kM, j + lM] = Z_II[i, j + ((l−k) mod n)·M]`
3. **Attention patterns** for query `i + kM` are the cyclic shift of those for ASU query `i`.

ZeUS exploits these facts to run the 18 diffusion transformer blocks only on the M ASU tokens
while still attending to all n·M keys, then broadcast the output to all chains.

Speedup: **n× per diffusion transformer block** (the most expensive component of each denoising step).

---

## What Already Exists

- `rfd3/inference/symmetry/`: full symmetry infrastructure (Cn/Dn frames, atom-array annotations)
- `rfd3/transforms/symmetry.py`: `AddSymmetryFeats` — populates `f["i s_sym_asu"]`, `f["sym_transform_id"]`, `f["sym_entity_id"]`
- `rfd3/inference/symmetry/symmetry_utils.py`: `apply_symmetry_to_xyz_atomwise` — enforces symmetry after each diffusion step
- `attention.py`: `sparse_pairbias_attention` — already sparse over keys; ZeUS shrinks the query dimension

---

## Not Changing

- Model weights (zero-code change for inference — ZeUS is a drop-in inference optimization)
- Training loop (ZeUS applies at inference time; training on symmetric data is separate)
- Input parsing / symmetry annotation pipeline

---

## Phases

### Phase 1 — ZeUS Data Structures
**New file**: `models/rfd3/src/rfd3/model/layers/zeus.py`

```python
@dataclass
class ZeUSIndexer:
    n_sym: int          # symmetry order (e.g. 3 for C3)
    M: int              # number of tokens in one subunit (ASU)
    asu_token_ids: Tensor  # [M] long — global token indices belonging to ASU
```

Helper functions (all in `zeus.py`):

| Function | Signature | Notes |
|---|---|---|
| `build_zeus_indexer` | `(f, sym_order) → ZeUSIndexer` | reads `f["is_sym_asu"]`, `f["atom_to_token_map"]` |
| `slice_asu_rows` | `(Z_II, asu_ids) → Tensor [B,M,I,c]` | extract ASU rows of full pair matrix |
| `broadcast_asu_to_all` | `(A_asu [B,M,c], n, M) → A_all [B,nM,c]` | tile ASU output to all subunits |
| `tile_asu_indices` | `(indices_asu [B,M,k]) → indices_all [B,nM,k]` | shift indices by subunit offset for full broadcast |

### Phase 2 — ZeUS Attention Kernel
**Modify**: `models/rfd3/src/rfd3/model/layers/attention.py`

Add `zeus_pairbias_attention`:
```python
def zeus_pairbias_attention(
    Q_asu,    # [B, M, c]       queries for ASU only
    K_all,    # [B, nM, c]      keys from all chains
    V_all,    # [B, nM, c]
    B_asu,    # [B, M, k, H]    pair bias: ASU queries × k nearest keys
    G_asu,    # [B, M, c]       gating
    indices,  # [B, M, k] long  key indices (can span all chains)
    H: int,
) -> Tensor:  # [B, M, c]
```

This is a thin wrapper around `sparse_pairbias_attention` with Q sliced to ASU only.
No new math — just explicit Q slicing before the existing kernel.

### Phase 3 — ZeUS-Aware `LocalAttentionPairBias`
**Modify**: `models/rfd3/src/rfd3/model/layers/attention.py` — `LocalAttentionPairBias.forward`

Add optional `zeus_indexer: ZeUSIndexer | None = None` parameter:

```
if zeus_indexer is not None:
    Q_asu = Q_L[:, zeus_indexer.asu_token_ids]          # [B, M, c]
    C_asu = C_L[:, zeus_indexer.asu_token_ids]          # [B, M, c_s]
    B_asu = P_LL[:, zeus_indexer.asu_token_ids, :, :]   # [B, M, I, c_pair]
    indices_asu = indices[:, zeus_indexer.asu_token_ids] # [B, M, k]
    # run attention on ASU only (M queries, nM keys)
    out_asu = zeus_pairbias_attention(Q_asu, K_all, V_all, b_asu, G_asu, indices_asu, H)
    # broadcast back to full sequence
    out_all = broadcast_asu_to_all(out_asu, zeus_indexer.n_sym, zeus_indexer.M)
    return out_all
else:
    # original path unchanged
    ...
```

Note: K and V are still projected from the **full** Q_L (all nM tokens), so inter-chain
information flows into ASU queries.

### Phase 4 — ZeUS in `LocalTokenTransformer`
**Modify**: `models/rfd3/src/rfd3/model/layers/blocks.py` — `LocalTokenTransformer.forward`

Add `zeus_indexer: ZeUSIndexer | None = None` parameter and pass it through to each block:

```python
for block in self.blocks:
    A_I = block(A_I, S_I, Z_II, indices=indices, zeus_indexer=zeus_indexer, ...)
```

The block-level `StructureLocalAtomTransformerBlock.forward` passes it to
`LocalAttentionPairBias.forward`.

The transition block (FFN after attention) can either:
- Run only on ASU and broadcast (saves n× FFN compute too) — Phase 4a
- Run on all tokens unchanged — Phase 4b (simpler, smaller gain)

Start with Phase 4b; add 4a if profiling shows the FFN is a bottleneck.

### Phase 5 — ZeUS in `RFD3DiffusionModule.process_`
**Modify**: `models/rfd3/src/rfd3/model/RFD3_diffusion_module.py`

In `process_()`, before calling `self.diffusion_transformer(...)`:

```python
zeus_indexer = None
if "is_sym_asu" in f and f["is_sym_asu"].any():
    zeus_indexer = build_zeus_indexer(f, sym_order=int(f["sym_entity_id"].max()) + 1)

A_I = self.diffusion_transformer(
    A_I, S_I, Z_II, f=f, X_L=...,
    zeus_indexer=zeus_indexer,
)
```

No changes to the encoder (`LocalAtomTransformer`) or decoder (`CompactStreamingDecoder`)
in this phase — those operate at atom level and are less expensive.

### Phase 6 — Pair Representation Folding (optional, phase 2)
`DiffusionTokenEncoder` currently builds `Z_II` as [B, nM, nM, c_z], which consumes O(n²M²) memory.

With ZeUS, only the ASU rows are used by the diffusion transformer. Phase 6 modifies
`DiffusionTokenEncoder` to produce only `Z_asu_II` [B, M, nM, c_z] (first-row blocks):

- The Pairformer blocks inside `DiffusionTokenEncoder` use triangle updates that are not
  immediately ZeUS-compatible. Two options:
  - **6a (simple)**: run full Pairformer, then slice ASU rows before passing to diffusion transformer
  - **6b (full)**: block-circulant Pairformer — run updates on [n, M, M] blocks only (n× memory + compute saving; requires re-implementing triangle updates for block-circulant structure)

Recommend 6a first (memory win only), then 6b if needed.

---

## Implementation Order

| Step | Change | Benefit |
|---|---|---|
| 1 | `zeus.py` helpers | infra only |
| 2 | `zeus_pairbias_attention` | infra only |
| 3 | `LocalAttentionPairBias` ZeUS path | attention n× speedup |
| 4b | `LocalTokenTransformer` ZeUS pass-through (attention only) | live speedup |
| 5 | `RFD3DiffusionModule` ZeUS detection | end-to-end path |
| 4a | FFN also on ASU only | +small gain |
| 6a | Slice Z_II to ASU rows | memory win |
| 6b | Block-circulant Pairformer | full O(n) memory |

---

## Correctness Tests

All tests live in `models/rfd3/tests/test_zeus.py`.

| Test | Check |
|---|---|
| `test_broadcast_is_inverse_of_slice` | `broadcast_asu_to_all(slice_asu_rows(A, ids))` reproduces A for a symmetric A |
| `test_zeus_matches_full_attention_c2` | ZeUS attention output = standard attention output on a synthetic C2 complex |
| `test_zeus_matches_full_attention_c3` | Same for C3 |
| `test_zeus_invariant_under_chain_permutation` | Permuting chains does not change ZeUS output |
| `test_zeus_forward_c3_regression` | Full `RFD3DiffusionModule.forward` with ZeUS vs. without on a C3 input — outputs must match within `atol=1e-4` |

The regression test is the critical one: it verifies ZeUS is a lossless optimization.

---

## Where to Wire ZeUS Into Inference

`models/rfd3/src/rfd3/model/RFD3_diffusion_module.py → process_()`:
- ZeUS activates only if `"is_sym_asu" in f and f["is_sym_asu"].any()`
- Gracefully falls back to original path for asymmetric inputs (no config change needed)

CLI users get the speedup automatically for symmetric designs — no flag required.

---

## Expected Speedup (Back-of-Envelope)

For a C3 trimer (n=3) with M=100 residues (L=300):
- Full attention: 300² = 90,000 token-pairs per head per layer
- ZeUS attention: 100 × 300 = 30,000 token-pairs per head per layer
- Speedup: **3×** per diffusion transformer layer

For a C9 nonamer (n=9) with M=100 residues (L=900):
- Full attention: 900² = 810,000 vs. ZeUS: 100 × 900 = 90,000
- Speedup: **9×** per layer

The 200-step sampler × 18 diffusion transformer blocks × n× savings per block means
the net wall-clock speedup on a C3 design is ~2–2.5× (accounting for the encoder/decoder
which are not ZeUS-optimized in phases 1–5).

---

## Files Changed

| File | Change |
|---|---|
| `models/rfd3/src/rfd3/model/layers/zeus.py` | new — ZeUSIndexer, helpers |
| `models/rfd3/src/rfd3/model/layers/attention.py` | add `zeus_pairbias_attention`; add ZeUS path to `LocalAttentionPairBias.forward` |
| `models/rfd3/src/rfd3/model/layers/blocks.py` | `LocalTokenTransformer.forward` and `StructureLocalAtomTransformerBlock.forward` accept `zeus_indexer` |
| `models/rfd3/src/rfd3/model/RFD3_diffusion_module.py` | `process_()` builds `ZeUSIndexer` from `f` and passes it |
| `models/rfd3/tests/test_zeus.py` | new — correctness tests |
