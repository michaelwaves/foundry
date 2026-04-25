import yaml
from typer.testing import CliRunner

from detectors.cli import app

runner = CliRunner()


def test_cli_score_smoke(synthetic_dataset, tmp_path):
    config_path = tmp_path / "score.yaml"
    config_path.write_text(yaml.safe_dump({
        "activations_path": synthetic_dataset["activations_path"],
        "labels_path": synthetic_dataset["labels_path"],
        "hook_name": "block8",
        "extractor": {"kind": "identity", "feature_dim": synthetic_dataset["activation_dim"]},
        "pooling": "last_step",
        "scorer": "auroc",
        "aggregation": "mean",
    }))
    out_dir = tmp_path / "score_out"
    result = runner.invoke(app, ["score", f"inputs={config_path}", f"out_dir={out_dir}"])
    assert result.exit_code == 0, result.output
    assert (out_dir / "feature_scores.parquet").exists()


def test_cli_missing_arg_errors(tmp_path):
    result = runner.invoke(app, ["score", "inputs=/nonexistent.yaml"])
    assert result.exit_code != 0
