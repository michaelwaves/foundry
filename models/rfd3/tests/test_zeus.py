import torch
import pytest

from rfd3.model.layers.zeus import ZeUSIndexer, broadcast_asu_to_all, build_zeus_indexer
from rfd3.model.layers.attention import LocalAttentionPairBias
from rfd3.model.layers.blocks import LocalTokenTransformer


# ─── helpers ──────────────────────────────────────────────────────────────────


def _make_feature_dict(n_sym: int, M: int, device="cpu") -> dict:
    """Minimal feature dict for a fully-symmetric Cn protein (1 atom per token)."""
    I = n_sym * M
    return {
        "atom_to_token_map": torch.arange(I, device=device),
        "is_sym_asu": torch.cat(
            [torch.ones(M, dtype=torch.bool), torch.zeros((n_sym - 1) * M, dtype=torch.bool)]
        ).to(device),
        "sym_transform_id": torch.cat(
            [torch.full((M,), k, dtype=torch.long) for k in range(n_sym)]
        ).to(device),
        # required by create_attention_indices
        "unindexing_pair_mask": torch.zeros(I, I, dtype=torch.bool, device=device),
        "asym_id": torch.cat(
            [torch.full((M,), k, dtype=torch.long) for k in range(n_sym)]
        ).to(device),
    }


def _make_block_circulant_Z_II(n_sym: int, M: int, c_z: int, B: int = 1) -> torch.Tensor:
    """Build a block-circulant pair matrix: Z[kM+i, lM+j] = block[(l-k) % n][i, j]."""
    I = n_sym * M
    blocks = torch.randn(n_sym, M, M, c_z)
    Z = torch.zeros(B, I, I, c_z)
    for k in range(n_sym):
        for l in range(n_sym):
            Z[:, k * M : (k + 1) * M, l * M : (l + 1) * M] = blocks[(l - k) % n_sym]
    return Z


def _make_all_to_all_indices(n_sym: int, M: int, B: int = 1) -> torch.Tensor:
    """Every query attends to every key (full dense indices)."""
    I = n_sym * M
    return torch.arange(I).view(1, 1, I).expand(B, I, I).contiguous()


# ─── unit tests ───────────────────────────────────────────────────────────────


def test_broadcast_asu_to_all_shape_and_values():
    B, n_sym, M, c = 2, 3, 5, 8
    A_asu = torch.randn(B, M, c)
    A_all = broadcast_asu_to_all(A_asu, n_sym)
    assert A_all.shape == (B, n_sym * M, c)
    for k in range(n_sym):
        assert torch.allclose(A_all[:, k * M : (k + 1) * M], A_asu)


def test_build_zeus_indexer_symmetric():
    for n_sym in [2, 3, 6]:
        M = 10
        f = _make_feature_dict(n_sym, M)
        zi = build_zeus_indexer(f)
        assert zi is not None
        assert zi.n_sym == n_sym
        assert zi.M == M


def test_build_zeus_indexer_returns_none_no_symmetry():
    f = _make_feature_dict(1, 10)
    assert build_zeus_indexer(f) is None


def test_build_zeus_indexer_returns_none_missing_keys():
    assert build_zeus_indexer({}) is None
    assert build_zeus_indexer({"is_sym_asu": torch.zeros(5, dtype=torch.bool)}) is None


def test_build_zeus_indexer_returns_none_fixed_motifs():
    n_sym, M, M_fixed = 3, 5, 2
    I_sym = n_sym * M
    I = I_sym + M_fixed
    f = {
        "atom_to_token_map": torch.arange(I),
        "is_sym_asu": torch.cat(
            [torch.ones(M, dtype=torch.bool), torch.zeros(I - M, dtype=torch.bool)]
        ),
        # fixed tokens have sym_transform_id == -1
        "sym_transform_id": torch.cat(
            [
                torch.cat([torch.full((M,), k) for k in range(n_sym)]),
                torch.full((M_fixed,), -1),
            ]
        ),
    }
    assert build_zeus_indexer(f) is None


# ─── attention correctness tests ──────────────────────────────────────────────


@pytest.mark.parametrize("n_sym", [2, 3, 4])
def test_zeus_attention_matches_full_for_symmetric_input(n_sym):
    """
    ZeUS attention output for ASU tokens must equal the standard attention output
    for ASU tokens when the input is symmetric and Z_II is block-circulant.
    """
    torch.manual_seed(0)
    M, c_a, c_s, c_z, n_head, B = 8, 64, 64, 64, 4, 1

    f = _make_feature_dict(n_sym, M)
    zi = build_zeus_indexer(f)
    assert zi is not None

    attn = LocalAttentionPairBias(
        c_a=c_a,
        c_s=c_s,
        c_pair=c_z,
        n_head=n_head,
        kq_norm=True,
    ).eval()

    A_asu = torch.randn(B, M, c_a)
    A_I = A_asu.repeat(1, n_sym, 1)
    C_asu = torch.randn(B, M, c_s)
    C_I = C_asu.repeat(1, n_sym, 1)
    Z_II = _make_block_circulant_Z_II(n_sym, M, c_z, B)
    indices = _make_all_to_all_indices(n_sym, M, B)

    with torch.no_grad():
        out_full = attn(A_I, C_I, Z_II, indices=indices)
        out_zeus = attn(A_I, C_I, Z_II, indices=indices, zeus_indexer=zi)

    assert out_zeus.shape == out_full.shape

    # ASU output must match
    assert torch.allclose(out_zeus[:, :M], out_full[:, :M], atol=1e-5), (
        f"ZeUS ASU mismatch: max_diff={torch.abs(out_zeus[:, :M] - out_full[:, :M]).max():.2e}"
    )

    # ZeUS output must be identical across all chains (it was broadcast)
    for k in range(1, n_sym):
        assert torch.allclose(out_zeus[:, k * M : (k + 1) * M], out_zeus[:, :M], atol=1e-9)


@pytest.mark.parametrize("n_sym", [2, 3])
def test_zeus_local_token_transformer_matches_full(n_sym):
    """Full LocalTokenTransformer with ZeUS matches standard output on symmetric input."""
    torch.manual_seed(1)
    M, c_t, c_z, c_s, B = 6, 64, 64, 64, 1
    n_block = 2

    diffusion_transformer_block = dict(
        n_head=4,
        kq_norm=True,
        dropout=0.0,
        no_residual_connection_between_attention_and_transition=False,
    )

    transformer = LocalTokenTransformer(
        c_token=c_t,
        c_tokenpair=c_z,
        c_s=c_s,
        n_block=n_block,
        diffusion_transformer_block=diffusion_transformer_block,
        n_local_tokens=M,
        n_keys=n_sym * M,
    ).eval()

    f = _make_feature_dict(n_sym, M)
    zi = build_zeus_indexer(f)

    A_asu = torch.randn(B, M, c_t)
    A_I = A_asu.repeat(1, n_sym, 1)
    S_asu = torch.randn(B, M, c_s)
    S_I = S_asu.repeat(1, n_sym, 1)
    Z_II = _make_block_circulant_Z_II(n_sym, M, c_z, B)

    # X_L: Ca positions — symmetric (same coords for each chain, just shifted in space)
    X_asu = torch.randn(B, M, 3)
    X_I = X_asu.repeat(1, n_sym, 1)

    with torch.no_grad():
        out_full = transformer(A_I, S_I, Z_II, f=f, X_L=X_I, full=False, zeus_indexer=None)
        out_zeus = transformer(A_I, S_I, Z_II, f=f, X_L=X_I, full=False, zeus_indexer=zi)

    assert out_zeus.shape == out_full.shape

    # ASU tokens should match
    assert torch.allclose(out_zeus[:, :M], out_full[:, :M], atol=1e-4), (
        f"LocalTokenTransformer ZeUS ASU mismatch: "
        f"max_diff={torch.abs(out_zeus[:, :M] - out_full[:, :M]).max():.2e}"
    )

    # ZeUS output is symmetric
    for k in range(1, n_sym):
        assert torch.allclose(out_zeus[:, k * M : (k + 1) * M], out_zeus[:, :M], atol=1e-9)


def test_zeus_disabled_for_asymmetric_input():
    """build_zeus_indexer returns None for asymmetric input; standard path is unchanged."""
    torch.manual_seed(2)
    M, c_a, c_s, c_z, n_head, B = 10, 32, 32, 32, 2, 1

    attn = LocalAttentionPairBias(c_a=c_a, c_s=c_s, c_pair=c_z, n_head=n_head).eval()

    A_I = torch.randn(B, M, c_a)
    C_I = torch.randn(B, M, c_s)
    Z_II = torch.randn(B, M, M, c_z)
    indices = torch.arange(M).view(1, 1, M).expand(B, M, M).contiguous()

    f = {
        "atom_to_token_map": torch.arange(M),
        "is_sym_asu": torch.zeros(M, dtype=torch.bool),  # no ASU → asymmetric
        "sym_transform_id": torch.zeros(M, dtype=torch.long),
    }
    assert build_zeus_indexer(f) is None

    with torch.no_grad():
        out = attn(A_I, C_I, Z_II, indices=indices, zeus_indexer=None)
    assert out.shape == (B, M, c_a)
