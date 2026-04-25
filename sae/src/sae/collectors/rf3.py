import json
from pathlib import Path

import yaml
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf


def collect(overrides: list[str]) -> None:
    """Run rf3 inference with activation hooks attached.

    Two ways to specify hooks (in priority order):
      1. CLI sidecar: `hooks=path/to/hooks.yaml`
      2. Embedded in the inputs JSON as a wrapper dict::
           {"run_config": {"activation_collection": {"hooks": [...]}}, "examples": [...]}
         The collector unpacks this — examples are written to a sidecar JSON that RF3
         actually reads, and run_config.activation_collection is set on the cfg.
    """
    overrides, hooks_path = _extract_hooks_path(overrides)
    overrides = _with_default_engine(overrides)
    with initialize_config_dir(config_dir=_config_dir(), version_base="1.3"):
        cfg = compose(config_name="inference", overrides=overrides)

    embedded_run_config = _maybe_unpack_examples_json(cfg)
    if embedded_run_config and "activation_collection" in embedded_run_config:
        cfg.activation_collection = OmegaConf.create(embedded_run_config["activation_collection"])

    if hooks_path is not None:
        cfg.activation_collection = OmegaConf.create(yaml.safe_load(Path(hooks_path).read_text()))

    from foundry.utils.logging import suppress_warnings
    from rf3.inference import run_inference

    with suppress_warnings(is_inference=True):
        run_inference(cfg)


def _maybe_unpack_examples_json(cfg) -> dict | None:
    """If cfg.inputs points at a {run_config, examples} wrapper JSON, write a sidecar
    file with just the examples list and repoint cfg.inputs at it. Returns the
    embedded run_config (or None if the inputs JSON isn't in wrapper format)."""
    inputs_path = _path_or_none(cfg.get("inputs"))
    if inputs_path is None or inputs_path.suffix != ".json":
        return None
    data = json.loads(inputs_path.read_text())
    if not (isinstance(data, dict) and "examples" in data and "run_config" in data):
        return None
    sidecar = inputs_path.with_name(inputs_path.stem + "__examples.json")
    sidecar.write_text(json.dumps(data["examples"]))
    cfg.inputs = str(sidecar)
    return data["run_config"]


def _path_or_none(inputs) -> Path | None:
    if isinstance(inputs, str):
        return Path(inputs)
    return None


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
