import torch.nn as nn
import torch
import h5py
import pickle
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional


class HookType(Enum):
    STATIC = "static"    # fires once per design (token_initializer)
    # fires once per denoising step (diffusion_module)
    DYNAMIC = "dynamic"


# A steering callback is invoked at every hook call with the current step index
# and returns (direction_tensor_of_shape_C, kind) where kind is "add" or
# "ablate", or (None, None) to skip steering at this step. The buffer broadcasts
# the (C,) direction across (..., C) outputs and casts to the layer's dtype.
SteeringCallback = Callable[[int], tuple[Optional[torch.Tensor], Optional[str]]]


@dataclass
class HookConfig:
    name: str
    module_path: str
    hook_type: HookType
    # Only relevant for DYNAMIC hooks like in model.diffusion_module:
    collect_every_n_steps: int = 1  # subsample denoising steps
    metadata: dict = field(default_factory=dict)


class ActivationBuffer:
    def __init__(
        self, model: nn.Module,  # e.g. RFD3 class
        out_dir: str,
        flush_every_n_collected: int = 10,  # flush to disk every 10 tensors collected
        steering_callbacks: dict[str, SteeringCallback] | None = None,
    ):
        self.model = model
        self.flush_every_n_collected = flush_every_n_collected
        self.out_dir = out_dir
        self._steering_callbacks = steering_callbacks or {}

        self._hooks = []
        self._buffers = {}        # {name: [tensors]}
        self._step_counts = {}    # {name: int} — raw call counter
        self._configs = {}        # {name: HookConfig}
        self._file = h5py.File(f"{out_dir}/activations.h5", 'a')

    def register(self, cfg: HookConfig):
        module = self.model.get_submodule(cfg.module_path)
        self._buffers[cfg.name] = []
        self._step_counts[cfg.name] = 0
        self._configs[cfg.name] = cfg

        grp = self._file.require_group(cfg.name)
        grp.attrs['hook_type'] = cfg.hook_type.value
        grp.attrs['module_path'] = cfg.module_path
        for k, v in cfg.metadata.items():
            grp.attrs[k] = v

        steering_cb = self._steering_callbacks.get(cfg.name)

        def hook(m, inp, out):
            count = self._step_counts[cfg.name]
            self._step_counts[cfg.name] += 1

            if steering_cb is not None:
                out = _apply_steering(out, steering_cb(count))

            if cfg.hook_type == HookType.STATIC:
                # Always collect, always just one call per design
                self._buffers[cfg.name].append(
                    out.detach().float().cpu().numpy())

            elif cfg.hook_type == HookType.DYNAMIC:
                # Subsample denoising steps
                if count % cfg.collect_every_n_steps == 0:
                    self._buffers[cfg.name].append(
                        out.detach().float().cpu().numpy())

            if len(self._buffers[cfg.name]) >= self.flush_every_n_collected:
                self._flush(cfg.name)

            return out

        self._hooks.append(module.register_forward_hook(hook))

    def _flush(self, name: str):
        if not self._buffers[name]:
            return

        grp = self._file.require_group(f"{name}/{self._current_example_id}")
        for i, act in enumerate(self._buffers[name]):
            # Each activation stored as separate dataset
            # key: step index for ordering
            existing = len(grp.keys())
            grp.create_dataset(
                str(existing),
                data=act,          # [B, N_atoms, C] or [B, L, C]
                compression='gzip',
                compression_opts=4,
            )

        self._buffers[name] = []
        self._file.flush()

    def store_metadata(self, example_id: str, pipeline_output: dict):
        metadata = {
            'feats': {k: v[0].cpu().numpy() if isinstance(v, torch.Tensor) else v
                      for k, v in pipeline_output['feats'].items()},
            't': pipeline_output['t'].cpu().numpy(),
            'specification': pipeline_output['specification'],
            'sampled_condition_name': pipeline_output['sampled_condition_name'],
            'atom_array': pipeline_output['atom_array'],
            'ground_truth': {k: v.cpu().numpy() if isinstance(v, torch.Tensor) else v
                             for k, v in pipeline_output['ground_truth'].items()},
        }
        with open(f"{self.out_dir}/{example_id}_metadata.pkl", 'wb') as f:
            pickle.dump(metadata, f)

    def on_design_start(self, example_id: str, pipeline_output: dict | None = None):
        if pipeline_output is not None:
            self.store_metadata(example_id, pipeline_output)
        self._current_example_id = example_id
        for name in self._step_counts:
            self._step_counts[name] = 0

    def on_design_end(self):
        for name in self._buffers:
            self._flush(name)

    def close(self):
        self.on_design_end()
        for h in self._hooks:
            h.remove()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _apply_steering(out: torch.Tensor, edit: tuple[Optional[torch.Tensor], Optional[str]]) -> torch.Tensor:
    direction, kind = edit
    if direction is None:
        return out
    v = direction.to(device=out.device, dtype=out.dtype)
    if kind == "add":
        return out + v
    if kind == "ablate":
        norm_sq = v.dot(v).clamp_min(1e-12)
        projection_scalar = (out @ v) / norm_sq      # (..., 1) scalar per row
        return out - projection_scalar.unsqueeze(-1) * v
    raise ValueError(f"unknown steering kind: {kind}")
