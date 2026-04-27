from dataclasses import dataclass
from typing import Any, Union


# A SteeringSpec is one entry under run_config.steering.<hook_name>. Multiple
# specs per hook compose by addition (steer entries) plus optional ablation.
@dataclass
class SteeringSpec:
    mode: str                                       # "sae_feature" or "raw_diff"
    type: str = "steer"                             # "steer" (add) or "ablate" (project out)
    apply_at_steps: Union[str, list[int]] = "all"   # "all" or explicit step list

    # sae_feature mode
    sae_path: str | None = None
    feature_id: int | None = None
    alpha: float = 1.0

    # raw_diff mode
    vector_path: str | None = None
    coeff: float = 1.0

    def fires_at(self, step: int) -> bool:
        if self.apply_at_steps == "all":
            return True
        if isinstance(self.apply_at_steps, list):
            return step in self.apply_at_steps
        raise ValueError(f"unsupported apply_at_steps: {self.apply_at_steps!r}")


def parse_specs(steering_section: dict[str, Any] | None) -> dict[str, list[SteeringSpec]]:
    """Parse run_config.steering = {hook_name: [spec_dict, ...]} into typed specs."""
    if not steering_section:
        return {}
    return {hook: [_one(d) for d in entries]
            for hook, entries in steering_section.items()}


def _one(spec: dict[str, Any]) -> SteeringSpec:
    mode = spec["mode"]
    if mode not in {"sae_feature", "raw_diff"}:
        raise ValueError(f"unknown steering mode: {mode}")
    if mode == "sae_feature" and (spec.get("sae_path") is None or spec.get("feature_id") is None):
        raise ValueError("sae_feature mode requires sae_path + feature_id")
    if mode == "raw_diff" and spec.get("vector_path") is None:
        raise ValueError("raw_diff mode requires vector_path")
    return SteeringSpec(
        mode=mode,
        type=spec.get("type", "steer"),
        apply_at_steps=spec.get("apply_at_steps", "all"),
        sae_path=spec.get("sae_path"),
        feature_id=spec.get("feature_id"),
        alpha=float(spec.get("alpha", 1.0)),
        vector_path=spec.get("vector_path"),
        coeff=float(spec.get("coeff", 1.0)),
    )
