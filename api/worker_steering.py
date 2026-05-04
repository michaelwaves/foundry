from pathlib import Path
from typing import Any

_TEMPLATE = """\
# @package steering
block12:
  - mode: sae_feature
    sae_path: ${{oc.env:FOUNDRY_ROOT}}/outputs/sae/2026-04-26_15-38-55/train/block12/final.pt
    feature_id: {feature_id}
    alpha: {alpha}
    apply_at_steps: {apply_at_steps}
"""


def generate_steering_yaml(steering: dict[str, Any] | None, work_dir: Path) -> Path | None:
    if not steering or steering.get("alpha", 0) == 0:
        return None
    yaml_path = work_dir / "steering.yaml"
    yaml_path.write_text(_TEMPLATE.format(
        feature_id=steering["feature_id"],
        alpha=steering["alpha"],
        apply_at_steps=steering.get("apply_at_steps", "all"),
    ))
    return yaml_path
