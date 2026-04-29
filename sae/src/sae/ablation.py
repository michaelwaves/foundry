"""Layer ablation: replace a block's output with its input (= prev block's output).

Implements the foldSAE localization method. Ablating block n is equivalent to
returning that block's first positional input unchanged, since residual blocks
take prev-block output as input — so the block's residual contribution is
dropped while the stream keeps flowing.
"""
from contextlib import contextmanager
from dataclasses import dataclass

import torch.nn as nn


@dataclass
class LayerAblationConfig:
    module_list_path: str
    indices: list[int]


@contextmanager
def ablate_layers(model: nn.Module, cfg: LayerAblationConfig):
    parent = model.get_submodule(cfg.module_list_path)
    handles = [parent[i].register_forward_hook(_passthrough) for i in cfg.indices]
    try:
        yield
    finally:
        for h in handles:
            h.remove()


def _passthrough(module, inputs, output):
    return inputs[0]
