"""Hydra-driven activation-collection orchestrator.

One config per (model, dataset) pair lives in `configs/`. This module reads the
config, builds the saffron inputs JSON, then shells out to `saffron collect`.

Usage:
  python -m tutorials.sae_collect.run_collect --config-name=rfd3_safeprotein
  python -m tutorials.sae_collect.run_collect --config-name=rf3_safeprotein \\
      subsample=100 out_dir=/tmp/test
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import hydra
from omegaconf import DictConfig

from detectors.datasets.sources import read_sources

from .builders import build_rf3_payload, build_rfd3_payload, load_or_seed_run_config


@hydra.main(version_base=None, config_path="configs", config_name="_base")
def main(cfg: DictConfig) -> None:
    out_dir = Path(cfg.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs_json = Path(cfg.inputs_json) if cfg.inputs_json else out_dir / "inputs.json"
    _write_inputs_json(cfg, inputs_json)
    _run_saffron_collect(cfg.model, inputs_json, out_dir)


def _write_inputs_json(cfg: DictConfig, out_json: Path) -> None:
    rows = read_sources(Path(cfg.sources))
    if cfg.subsample and cfg.subsample < len(rows):
        rows = random.Random(cfg.seed).sample(rows, cfg.subsample)
    run_config = load_or_seed_run_config(out_json, Path(cfg.hooks_yaml))
    if cfg.model == "rfd3":
        body, skipped = build_rfd3_payload(rows, cfg.partial_t)
        payload = {"run_config": run_config, **body}
        kept = len(body)
    elif cfg.model == "rf3":
        examples, skipped = build_rf3_payload(rows)
        payload = {"run_config": run_config, "examples": examples}
        kept = len(examples)
    else:
        raise ValueError(f"unknown model: {cfg.model}")
    out_json.write_text(json.dumps(payload, indent=2))
    for line in skipped:
        print(f"skip {line}")
    print(f"wrote {kept} examples -> {out_json} (skipped {len(skipped)})")


def _run_saffron_collect(model: str, inputs_json: Path, out_dir: Path) -> None:
    cmd = ["saffron", "collect", f"model={model}",
           f"inputs={inputs_json}", f"out_dir={out_dir}"]
    print(f"running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
