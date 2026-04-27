from typing import Callable, Optional

import torch

from sae.steering.config import SteeringSpec
from sae.steering.vectors import direction_from_spec


def build_callbacks(
    specs_per_hook: dict[str, list[SteeringSpec]],
) -> dict[str, Callable[[int], tuple[Optional[torch.Tensor], Optional[str]]]]:
    """One callback per hook. Each call returns the composed direction for the
    current step plus the operation kind ("add" or "ablate"), or (None, None)
    when no spec fires at this step.

    Composition rule: at most one ablate spec per hook (validated). All steer
    specs that fire at the step are summed into a single "add" direction.
    Ablate, if active, is returned instead — engines should call ablate first
    in the hook (cleaner semantics) — but for the v1 API we return a single
    edit per call; see plan.md for future composition details.
    """
    callbacks: dict[str, Callable[[int], tuple]] = {}
    for hook_name, specs in specs_per_hook.items():
        steer_specs = [s for s in specs if s.type == "steer"]
        ablate_specs = [s for s in specs if s.type == "ablate"]
        if len(ablate_specs) > 1:
            raise ValueError(f"hook {hook_name!r}: at most one ablate spec supported in v1")
        steer_directions = [direction_from_spec(s) for s in steer_specs]
        ablate_direction = direction_from_spec(ablate_specs[0]) if ablate_specs else None

        callbacks[hook_name] = _make_callback(steer_specs, steer_directions, ablate_specs, ablate_direction)
    return callbacks


def _make_callback(
    steer_specs: list[SteeringSpec],
    steer_directions: list[torch.Tensor],
    ablate_specs: list[SteeringSpec],
    ablate_direction: torch.Tensor | None,
):
    def callback(step: int) -> tuple[torch.Tensor | None, str | None]:
        if ablate_specs and ablate_specs[0].fires_at(step):
            return ablate_direction, "ablate"
        active = [d for s, d in zip(steer_specs, steer_directions) if s.fires_at(step)]
        if not active:
            return None, None
        return torch.stack(active).sum(dim=0), "add"

    return callback
