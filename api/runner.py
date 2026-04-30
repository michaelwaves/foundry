import asyncio
import json
import uuid
from pathlib import Path

import sae

from api.models import Job, JobStatus
from api.store import save

FOUNDRY_ROOT = Path(__file__).resolve().parent.parent
SAE_STEERING_CONFIGS = Path(sae.__file__).resolve().parent / "configs" / "steering"
JOBS_DIR = FOUNDRY_ROOT / "api" / "cache"

_STEERING_TEMPLATE = """\
# @package steering
block12:
  - mode: sae_feature
    sae_path: ${{oc.env:FOUNDRY_ROOT,{foundry_root}}}/outputs/sae/2026-04-26_15-38-55/train/block12/final.pt
    feature_id: 639
    alpha: {alpha}
    apply_at_steps: all
"""


def create_job() -> Job:
    job = Job(id=str(uuid.uuid4()))
    save(job)
    return job


async def launch(job: Job, alpha: float, motif_bytes: bytes | None) -> None:
    job.status = JobStatus.running
    save(job)
    steering_name = None
    try:
        work_dir = JOBS_DIR / job.id
        work_dir.mkdir(parents=True, exist_ok=True)
        inputs_path = _write_inputs(work_dir, job.id, motif_bytes)
        out_dir = work_dir / "out"
        out_dir.mkdir()
        if alpha != 0.0:
            steering_name = _write_steering_yaml(job.id, alpha)
        await _run_saffron(inputs_path, steering_name, out_dir, job)
        job.output_path = str(_find_cif(out_dir))
        job.status = JobStatus.done
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
    finally:
        if steering_name:
            _delete_steering_yaml(job.id)
        save(job)


def _write_inputs(work_dir: Path, design_name: str, motif_bytes: bytes | None) -> Path:
    if motif_bytes is not None:
        pdb_path = work_dir / "motif.pdb"
        pdb_path.write_bytes(motif_bytes)
        spec = {"input": str(pdb_path), "select_fixed_atoms": True}
    else:
        spec = {"length": "100-150"}
    inputs_path = work_dir / "inputs.json"
    inputs_path.write_text(json.dumps({design_name: spec}))
    return inputs_path


def _write_steering_yaml(job_id: str, alpha: float) -> str:
    name = f"_api_{job_id}"
    content = _STEERING_TEMPLATE.format(foundry_root=FOUNDRY_ROOT, alpha=alpha)
    (SAE_STEERING_CONFIGS / f"{name}.yaml").write_text(content)
    return name


def _delete_steering_yaml(job_id: str) -> None:
    (SAE_STEERING_CONFIGS / f"_api_{job_id}.yaml").unlink(missing_ok=True)


async def _run_saffron(
    inputs_path: Path, steering_name: str | None, out_dir: Path, job: "Job"
) -> None:
    cmd = [
        "saffron", "steer", "model=rfd3",
        f"inputs={inputs_path}",
        f"out_dir={out_dir}",
    ]
    if steering_name:
        cmd += ["hooks=rfd3_steer_only", f"steering={steering_name}"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(FOUNDRY_ROOT),
    )

    async def drain(stream: asyncio.StreamReader) -> None:
        async for raw in stream:
            line = raw.decode().rstrip()
            if line:
                job.logs.append(line)
                save(job)

    await asyncio.gather(drain(proc.stdout), drain(proc.stderr))
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"saffron exited {proc.returncode}")


def _find_cif(out_dir: Path) -> Path:
    cifs = sorted(out_dir.glob("*.cif.gz"))
    if not cifs:
        raise FileNotFoundError(f"no .cif.gz output found in {out_dir}")
    return cifs[0]
