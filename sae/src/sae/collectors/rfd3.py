from pathlib import Path

from hydra import compose, initialize_config_dir


def collect(overrides: list[str]) -> None:
    """Run rfd3 inference with activation hooks attached."""
    with initialize_config_dir(config_dir=_config_dir(), version_base="1.3"):
        cfg = compose(config_name="inference",
                      overrides=_with_default_engine(overrides))
    from foundry.utils.logging import suppress_warnings
    from rfd3.run_inference import run_inference

    with suppress_warnings(is_inference=True):
        run_inference(cfg)


def _config_dir() -> str:
    import rfd3

    package_root = Path(rfd3.__file__).resolve().parent
    dev = package_root.parent.parent / "configs"
    return str(dev if dev.exists() else package_root / "configs")


def _with_default_engine(overrides: list[str]) -> list[str]:
    if any(arg.startswith("inference_engine=") for arg in overrides):
        return list(overrides)
    return [*overrides, "inference_engine=rfdiffusion3"]
