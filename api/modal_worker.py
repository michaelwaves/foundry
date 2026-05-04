from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import modal

if TYPE_CHECKING:
    from worker_logs import RedisLogger

VOLUME_PATH = "/weights"
TIMEOUT_SECONDS = 1800

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "build-essential")
    .pip_install(
        "rc-foundry[rfd3,api] @ git+https://github.com/michaelwaves/foundry@modal",
        "rc-foundry-sae @ git+https://github.com/michaelwaves/foundry@modal#subdirectory=sae",
        "tmtools>=0.3.0",
        "supabase>=2.9",
        "redis>=5.2",
    )
    .env({
        "FOUNDRY_ROOT": VOLUME_PATH,
        "FOUNDRY_CHECKPOINT_DIRS": f"{VOLUME_PATH}/checkpoints",
    })
    .add_local_python_source("worker_inputs", "worker_steering", "worker_logs", "worker_output")
)

volume = modal.Volume.from_name("foundry-weights", create_if_missing=True)
app = modal.App(
    "foundry",
    image=image,
    secrets=[modal.Secret.from_name("foundry-secrets")],
)


@app.function(gpu="A10G", timeout=TIMEOUT_SECONDS, volumes={VOLUME_PATH: volume})
def run_job(job_id: str, user_id: str, config: dict[str, Any]) -> None:
    from supabase import create_client

    from worker_logs import RedisLogger
    from worker_steering import generate_steering_yaml
    from worker_inputs import build_inputs_json, fetch_motif_pdb
    from worker_output import upload_output

    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    logger = RedisLogger(job_id)
    logger.publish_status("running")
    db.table("jobs").update({"status": "running"}).eq("id", job_id).execute()

    steering_yaml: Path | None = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            motif_path = fetch_motif_pdb(
                db, config.get("pdb_storage_path"), work_dir)
            inputs_path = build_inputs_json(work_dir, config, motif_path)
            steering_yaml = generate_steering_yaml(
                config.get("steering"), work_dir)
            output_path = _run_saffron(
                inputs_path, steering_yaml, work_dir, config["diffusion_steps"],
                bool(config.get("symmetry")), bool(config.get("disable_zeus")), logger)
            output_url = upload_output(db, user_id, job_id, output_path)
        db.table("jobs").update({"status": "done", "output_url": output_url}).eq(
            "id", job_id).execute()
        logger.publish_status("done")
    except Exception as exc:
        message = str(exc)
        db.table("jobs").update({"status": "failed", "error": message}).eq(
            "id", job_id).execute()
        logger.publish_status("failed", message)
    finally:
        if steering_yaml is not None:
            steering_yaml.unlink(missing_ok=True)
        logger.publish_done()
        logger.close()


def _run_saffron(
    inputs_path: Path,
    steering_yaml: Path | None,
    work_dir: Path,
    diffusion_steps: int,
    symmetric: bool,
    disable_zeus: bool,
    logger: RedisLogger,
) -> Path:
    out_dir = work_dir / "out"
    out_dir.mkdir()
    cmd = [
        "saffron", "steer", "model=rfd3",
        f"inputs={inputs_path}",
        f"out_dir={out_dir}",
        f"inference_sampler.num_timesteps={diffusion_steps}",
    ]
    if symmetric:
        cmd += ["inference_sampler.kind=symmetry", "diffusion_batch_size=1"]
    if disable_zeus:
        cmd += ["disable_zeus=true"]
    if steering_yaml:
        cmd += ["hooks=rfd3_steer_only", f"steering={steering_yaml.stem}"]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "FOUNDRY_ROOT": VOLUME_PATH},
    )
    assert process.stdout is not None
    for line in process.stdout:
        stripped = line.rstrip()
        if stripped:
            logger.publish_log(stripped)
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"saffron exited {process.returncode}")
    return _find_output_cif(out_dir)


def _find_output_cif(out_dir: Path) -> Path:
    matches = sorted(out_dir.glob("**/*.cif.gz"))
    if not matches:
        raise FileNotFoundError(f"no .cif.gz output in {out_dir}")
    return matches[0]
