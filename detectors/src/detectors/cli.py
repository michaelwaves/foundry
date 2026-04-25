import json
from pathlib import Path

import typer
import yaml

from detectors.pipelines.fit import run_fit
from detectors.pipelines.labels import run_labels
from detectors.pipelines.score import run_score
from detectors.pipelines.screen import run_screen

app = typer.Typer(add_completion=False)
_EXTRA_ARGS = {"allow_extra_args": True, "ignore_unknown_options": True}


@app.command(context_settings=_EXTRA_ARGS)
def labels(ctx: typer.Context) -> None:
    """Build labels.csv from labelled FASTAs + activations.h5."""
    run_labels(_load_config(ctx.args))


@app.command(context_settings=_EXTRA_ARGS)
def score(ctx: typer.Context) -> None:
    """Rank features by class correlation."""
    run_score(_load_config(ctx.args))


@app.command(context_settings=_EXTRA_ARGS)
def fit(ctx: typer.Context) -> None:
    """Train a detector and save the bundle."""
    run_fit(_load_config(ctx.args))


@app.command(context_settings=_EXTRA_ARGS)
def screen(ctx: typer.Context) -> None:
    """Score new designs with a saved detector."""
    run_screen(_load_config(ctx.args))


@app.command(context_settings=_EXTRA_ARGS)
def evaluate(ctx: typer.Context) -> None:
    """Run screen + write held-out metrics."""
    config = _load_config(ctx.args)
    report = run_screen(config)
    _write_eval_metrics(config, report)


def _load_config(raw_args: list[str]) -> dict:
    inputs_path = _required_arg(raw_args, "inputs")
    out_dir = _required_arg(raw_args, "out_dir")
    config = _read_inputs_file(Path(inputs_path))
    config["out_dir"] = out_dir
    return config


def _required_arg(raw_args: list[str], key: str) -> str:
    for arg in raw_args:
        if arg.startswith(f"{key}="):
            return arg.split("=", 1)[1]
    raise ValueError(f"missing required arg: {key}=<value>")


def _read_inputs_file(path: Path) -> dict:
    suffix = path.suffix.lower()
    text = path.read_text()
    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if suffix == ".json":
        return json.loads(text)
    raise ValueError(f"unsupported config extension: {suffix}")


def _write_eval_metrics(config: dict, report) -> None:
    import pandas as pd

    from detectors.scorers.auroc import auroc_vectorized

    labels_df = pd.read_csv(config["labels_path"]).set_index("design_id")
    aligned = report.set_index("design_id").join(labels_df, how="inner")
    accuracy = float((aligned["prediction"] == aligned["label"]).mean())
    auroc = float(auroc_vectorized(aligned[["probability"]].to_numpy(), aligned["label"].to_numpy())[0])
    metrics = {"accuracy": accuracy, "auroc": auroc, "n_designs": int(len(aligned))}
    (Path(config["out_dir"]) / "eval_metrics.json").write_text(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    app()
