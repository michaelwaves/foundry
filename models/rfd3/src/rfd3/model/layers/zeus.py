import os
from dataclasses import dataclass

import torch
from torch import Tensor


@dataclass
class ZeUSIndexer:
    n_sym: int
    M: int


def build_zeus_indexer(f: dict) -> ZeUSIndexer | None:
    """
    Build a ZeUSIndexer from feature dict, or return None if the input is not
    fully symmetric (fixed motifs present, only one subunit, or missing feats).
    """
    if os.environ.get("RFD3_DISABLE_ZEUS") == "1":
        return None
    if "is_sym_asu" not in f or "sym_transform_id" not in f:
        return None

    tok_idx = f["atom_to_token_map"]
    is_sym_asu = torch.as_tensor(f["is_sym_asu"], dtype=torch.bool).to(tok_idx.device)
    if not is_sym_asu.any():
        return None

    sym_t = torch.as_tensor(f["sym_transform_id"]).to(tok_idx.device)
    if (sym_t == -1).any():
        return None  # fixed / unsymmetric motifs present

    I = int(tok_idx.max().item()) + 1
    n_sym = int(sym_t.max().item()) + 1
    if n_sym <= 1:
        return None

    token_asu = torch.zeros(I, dtype=torch.bool, device=tok_idx.device)
    token_asu.scatter_(0, tok_idx[is_sym_asu].long(), True)
    M = int(token_asu.sum().item())

    if n_sym * M != I:
        return None  # token count inconsistent with symmetry

    # ASU must be the first M tokens (tokens 0..M-1)
    if not (token_asu[:M].all() and not token_asu[M:].any()):
        return None

    return ZeUSIndexer(n_sym=n_sym, M=M)


def broadcast_asu_to_all(A_asu: Tensor, n_sym: int) -> Tensor:
    """[B, M, c] → [B, n*M, c] by tiling the ASU representation."""
    return A_asu.repeat(1, n_sym, 1)
