import json
import os
from pathlib import Path

import typer
import yaml
from hydra import compose, initialize_config_dir
from omegaconf import DictConfig, OmegaConf

app = typer.Typer(add_completion=False)

_CONFIG_DIR = str(Path(__file__).parent / "configs")
_EXTRA_ARGS = {"allow_extra_args": True, "ignore_unknown_options": True}


@app.command(context_settings=_EXTRA_ARGS)
def collect(ctx: typer.Context) -> None:
    """Collect activations by running a model's inference with hooks."""
    model, overrides = _split_model_override(ctx.args)
    from sae.collectors import dispatch

    dispatch(model, overrides)


@app.command(context_settings=_EXTRA_ARGS)
def train(ctx: typer.Context) -> None:
    """Train a sparse autoencoder."""
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF",
                          "expandable_segments:True")
    cfg = _build_config(_CONFIG_DIR, "train", ctx.args)
    from sae.train import run_training

    run_training(cfg)


@app.command(name="eval", context_settings=_EXTRA_ARGS)
def eval_(ctx: typer.Context) -> None:
    """Evaluate a trained sparse autoencoder."""
    cfg = _build_config(_CONFIG_DIR, "eval", ctx.args)
    from sae.eval import run_eval

    run_eval(cfg)


@app.command(context_settings=_EXTRA_ARGS)
def screen(ctx: typer.Context) -> None:
    """Screen activations with a saved detector bundle. Alias for `detect screen`."""
    from detectors.cli import screen as detect_screen

    detect_screen(ctx)


@app.command(context_settings=_EXTRA_ARGS)
def steer(ctx: typer.Context) -> None:
    """Run a model's inference with steering directions added to chosen hooks.

    Same dispatch as `saffron collect` — the inputs JSON's run_config carries a
    `steering` block alongside `activation_collection`. Each engine reads it
    and wires steering callbacks into the activation buffer.
    """
    model, overrides = _split_model_override(ctx.args)
    from sae.collectors import dispatch

    dispatch(model, overrides)


@app.command(name="compute_steering_vector", context_settings=_EXTRA_ARGS)
def compute_steering_vector(ctx: typer.Context) -> None:
    """Compute mean(positives) - mean(negatives) per hook from two h5s.

    Outputs one <hook>.pt per hook plus a meta.json. Used by raw_diff steering;
    sae_feature steering doesn't need this step.
    """
    cfg = _build_config(_CONFIG_DIR, "compute_steering_vector", ctx.args)
    from sae.steering.compute_diff import run_compute_diff

    run_compute_diff(cfg)


def _build_config(config_dir: str, config_name: str, raw_args: list[str]) -> DictConfig:
    overrides, inputs_path = _split_inputs_override(raw_args)
    with initialize_config_dir(config_dir=config_dir, version_base="1.3"):
        cfg = compose(
            config_name=config_name,
            overrides=overrides,
        )
    if inputs_path is not None:
        cfg = OmegaConf.merge(cfg, _load_overrides_file(inputs_path))
    return cfg


def _split_model_override(args: list[str]) -> tuple[str, list[str]]:
    model: str | None = None
    overrides: list[str] = []
    for arg in args:
        if arg.startswith("model="):
            model = arg.split("=", 1)[1]
        else:
            overrides.append(arg)
    if model is None:
        raise ValueError(
            "saffron collect requires model=<name> (e.g. model=rfd3)")
    return model, overrides


def _split_inputs_override(args: list[str]) -> tuple[list[str], str | None]:
    overrides: list[str] = []
    inputs_path: str | None = None
    for arg in args:
        if arg.startswith("inputs="):
            inputs_path = arg.split("=", 1)[1]
        else:
            overrides.append(arg)
    return overrides, inputs_path


def _load_overrides_file(path: str) -> DictConfig:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(file_path.read_text())
    elif suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(file_path.read_text())
    else:
        raise ValueError(f"unsupported inputs file extension: {suffix}")
    return OmegaConf.create(data)


if __name__ == "__main__":
    app()
