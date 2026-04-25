from pathlib import Path

import yaml
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf


def collect(overrides: list[str]) -> None:
    """Run rf3 inference with activation hooks attached.

    Accepts an extra `hooks=path/to/hooks.yaml` arg whose contents are merged into
    `inference_engine.activation_collection`. RF3's input JSON is a list (not a dict),
    so hooks can't be inlined as they are for RFD3.
    """
    overrides, hooks_path = _extract_hooks_path(overrides)
    overrides = _with_default_engine(overrides)
    with initialize_config_dir(config_dir=_config_dir(), version_base="1.3"):
        cfg = compose(config_name="inference", overrides=overrides)
    if hooks_path is not None:
        # rf3.yaml uses `# @package _global_`, so engine init params live at top level
        hooks_cfg = yaml.safe_load(Path(hooks_path).read_text())
        cfg.activation_collection = OmegaConf.create(hooks_cfg)
    from foundry.utils.logging import suppress_warnings
    from rf3.inference import run_inference

    with suppress_warnings(is_inference=True):
        run_inference(cfg)


def _extract_hooks_path(overrides: list[str]) -> tuple[list[str], str | None]:
    remaining: list[str] = []
    hooks_path: str | None = None
    for arg in overrides:
        if arg.startswith("hooks="):
            hooks_path = arg.split("=", 1)[1]
        else:
            remaining.append(arg)
    return remaining, hooks_path


def _config_dir() -> str:
    import rf3

    package_root = Path(rf3.__file__).resolve().parent
    dev = package_root.parent.parent / "configs"
    return str(dev if dev.exists() else package_root / "configs")


def _with_default_engine(overrides: list[str]) -> list[str]:
    if any(arg.startswith("inference_engine=") for arg in overrides):
        return list(overrides)
    return [*overrides, "inference_engine=rf3"]
