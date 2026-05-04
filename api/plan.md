# Modal Migration Plan — Foundry API

## Target Architecture

```
Browser
   │
   ├─ POST /jobs ────────► Railway FastAPI ──► modal_worker.run_job.spawn()
   │                            │                        │
   │                            └─► Supabase Postgres    │
   │                                (insert job row)     │
   │                                                     ▼
   └─ GET /jobs/:id/stream ─► Railway SSE ◄── Redis pub/sub
                                  ▲                      │
                                  │                      ▼
                                  └── Modal GPU worker ──┤
                                           │             │
                                           ├─► Redis (publish log lines)
                                           ├─► Supabase Postgres (status updates)
                                           └─► Supabase Storage (output CIF)
```

## Current State

| Concern | Now | After |
|---|---|---|
| Job store | In-memory dict (`store.py`) | Supabase Postgres |
| Job execution | subprocess `saffron steer` | Modal GPU function |
| Log streaming | Poll in-memory list (SSE) | Redis pub/sub (SSE) |
| Output files | Local `cache/{job_id}/` | Supabase Storage |

---

## Phase 1 — Infrastructure Setup

### 1.1 Supabase

Create the `jobs` table:

```sql
create table jobs (
  id         uuid primary key default gen_random_uuid(),
  status     text not null default 'pending',
  error      text,
  output_url text,
  created_at timestamptz not null default now()
    created_by uuid, add user
);
```

Create a storage bucket named `outputs` (private, signed URLs for download).

Environment variables needed:
- `SUPABASE_URL`
- `SUPABASE_KEY` (service-role key, never anon key — workers write to storage)

### 1.2 Redis on Railway

Add the Redis addon to the Railway project (one click). This gives:
- `REDIS_URL` (e.g. `redis://default:password@host:6379`)

### 1.3 Modal Secrets

Create a Modal secret named `foundry-secrets` with:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `REDIS_URL`

### 1.4 Modal Volume for Model Weights

```bash
modal volume create foundry-weights
```

Then run once to populate:

```bash
modal run scripts/upload_weights.py  # see Phase 2.1
```

---

## Phase 2 — New Files

### 2.1 `modal_worker.py` — Modal GPU function

This is the core new file. It:
- Defines the Modal image (CUDA + foundry[rfd3,sae] installed)
- Mounts the weights volume at `/weights`
- Exposes `run_job(job_id, job_config)` as a Modal function
- Runs `saffron steer`, streams logs to Redis, writes status to Supabase, uploads output

Key design decisions:
- Use `gpu="A10G"`
- `timeout=600` (10 min max per job)
- Log each stdout/stderr line immediately to Redis channel `logs:{job_id}`
- On completion, upload `output.cif.gz` to Supabase Storage and write signed URL to job row
- On failure, write error message to job row and set status `failed`

```python
# api/modal_worker.py

import modal, os, subprocess, redis, asyncio
from supabase import create_client
from pathlib import Path

VOLUME_PATH = "/weights"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("foundry[rfd3,sae] @ git+...", "supabase", "redis")
)

volume = modal.Volume.from_name("foundry-weights", create_if_missing=True)
app = modal.App("foundry", image=image, secrets=[modal.Secret.from_name("foundry-secrets")])


@app.function(gpu="A10G", timeout=600, volumes={VOLUME_PATH: volume})
def run_job(job_id: str, job_config: dict) -> None:
    r = redis.from_url(os.environ["REDIS_URL"])
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    channel = f"logs:{job_id}"

    def publish(line: str) -> None:
        r.publish(channel, line)

    def set_status(status: str, **kwargs) -> None:
        db.table("jobs").update({"status": status, **kwargs}).eq("id", job_id).execute()

    set_status("running")
    try:
        output_path = _run_inference(job_id, job_config, publish)
        output_url = _upload_output(db, job_id, output_path)
        set_status("done", output_url=output_url)
    except Exception as exc:
        set_status("failed", error=str(exc))
    finally:
        r.publish(channel, "__done__")
```

### 2.2 `db.py` — Supabase job CRUD

Thin wrapper over `supabase-py`. Replaces `store.py`.

```python
# api/db.py
from dataclasses import dataclass
from enum import StrEnum
from supabase import create_client, Client


class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus
    error: str | None
    output_url: str | None


def make_client(url: str, key: str) -> Client:
    return create_client(url, key)


def insert_job(db: Client, job_id: str) -> None:
    db.table("jobs").insert({"id": job_id, "status": "pending"}).execute()


def get_job(db: Client, job_id: str) -> Job | None:
    row = db.table("jobs").select("*").eq("id", job_id).maybe_single().execute()
    if row.data is None:
        return None
    return Job(**row.data)
```

### 2.3 `redis_client.py` — pub/sub helper

```python
# api/redis_client.py
import os, redis

def make_redis() -> redis.Redis:
    return redis.from_url(os.environ["REDIS_URL"])

def subscribe_logs(r: redis.Redis, job_id: str):
    ps = r.pubsub()
    ps.subscribe(f"logs:{job_id}")
    return ps
```

### 2.4 `scripts/upload_weights.py` — one-time weight upload

Run locally once to populate the Modal volume with RFD3 weights.

```bash
modal run api/scripts/upload_weights.py --weights-dir ~/.cache/foundry/checkpoints
```

---

## Phase 3 — Modified Files

### 3.1 `runner.py` — spawn Modal instead of subprocess

**Remove:** `subprocess.Popen`, in-memory log appending, local cache dir creation.

**Add:** call `modal_worker.run_job.spawn(job_id, config_dict)`.

The runner becomes ~20 lines. It builds `job_config` (same data currently written to `inputs.json` + steering params) as a plain dict, inserts the job row in Supabase, then spawns the Modal function.

```python
# api/runner.py
import uuid
from .db import insert_job
from .modal_worker import run_job

def submit_job(db, alpha: float, partial_t: float, motif_bytes: bytes | None) -> str:
    job_id = str(uuid.uuid4())
    job_config = build_job_config(alpha, partial_t, motif_bytes)
    insert_job(db, job_id)
    run_job.spawn(job_id, job_config)
    return job_id
```

### 3.2 `main.py` — wire Redis SSE + Supabase store

**`POST /jobs`**: call `runner.submit_job(db, ...)`.

**`GET /jobs/{job_id}`**: call `db.get_job(db_client, job_id)`.

**`GET /jobs/{job_id}/stream`** (SSE): subscribe to Redis channel instead of polling in-memory list.

```python
async def stream_logs(job_id: str):
    ps = subscribe_logs(redis_client, job_id)
    async for message in _iter_pubsub(ps):
        if message["data"] == "__done__":
            break
        yield f"data: {message['data']}\n\n"
```

**`GET /jobs/{job_id}/output`**: redirect to `job.output_url` (Supabase signed URL, 1-hour TTL).

### 3.3 `models.py` — add `output_url` field

Add `output_url: str | None = None` to `Job`. Remove `logs: list[str]` since logs now live in Redis only.

### 3.4 `store.py` — delete

No longer needed. Job state lives in Supabase.

---

## Phase 4 — Weight Loading in Modal Volume

Three artifact trees must live in the Modal Volume (mounted at `/weights`):

| Artifact | Local path | Volume path |
|---|---|---|
| RFD3 model weights | `~/.cache/foundry/checkpoints/rfd3` | `/weights/checkpoints/rfd3` |
| SAE checkpoint | `outputs/sae/2026-04-26_15-38-55/` | `/weights/outputs/sae/2026-04-26_15-38-55/` |
| Steering vectors | `outputs/steering/vectors/` | `/weights/outputs/steering/vectors/` |

The Modal worker sets `FOUNDRY_ROOT=/weights` so that OmegaConf `${oc.env:FOUNDRY_ROOT}` interpolations in steering configs resolve correctly.

`scripts/upload_weights.py` uploads all three trees in one pass:

```bash
modal run api/scripts/upload_weights.py \
  --rfd3-ckpt ~/.cache/foundry/checkpoints/rfd3 \
  --outputs-dir /mnt/nw/home/m.yu/repos/foundry/outputs
```

The worker env var in `modal_worker.py`:
```python
@app.function(
    gpu="A10G",
    timeout=600,
    volumes={VOLUME_PATH: volume},
    env={"FOUNDRY_ROOT": VOLUME_PATH},
)
```

---

## Phase 5 — SAE / Steering in Modal Worker

Steering paths are referenced two ways in the codebase:

**Good — `${oc.env:FOUNDRY_ROOT}` interpolation** (works once `FOUNDRY_ROOT=/weights` is set):
- `sae/configs/steering/sae_block12_f639.yaml`
- `sae/configs/steering/null_block12_f639.yaml`
- `sae/configs/steering/raw_diff_block12.yaml`
- `runner.py` YAML template

**Bad — hardcoded absolute paths** (will break in Modal, must be fixed before deploying):
- `sae/configs/steering/ablate_block12_f639.yaml`
- `sae/configs/steering/ablate_block12_f639_alpha2.yaml`
- `sae/configs/steering/ablate_block12_f639_alpha4.yaml`
- `sae/configs/steering/ablate_block12_f639_alpha8.yaml`
- `sae/configs/steering/rawdiff_neg_block12_c1.yaml`
- `sae/configs/steering/rawdiff_neg_block12_c2.yaml`
- `sae/configs/steering/rawdiff_neg_block12_c4.yaml`
- `sae/configs/steering/rawdiff_neg_block12_c8.yaml`

Fix: replace every hardcoded `/mnt/nw/home/m.yu/repos/foundry/` with `${oc.env:FOUNDRY_ROOT,/mnt/nw/home/m.yu/repos/foundry}/` in all eight files. This is a safe local fallback that keeps the configs working on your machine too.

The Modal image needs `foundry[rfd3,sae]` installed so `saffron steer` is available. The steering YAML configs ship inside the installed package, so no extra copy step is needed — only the weight files need the volume.

---

## Implementation Order

1. **Supabase:** create `jobs` table + `outputs` bucket
2. **Railway:** add Redis addon, verify `REDIS_URL`
3. **Fix steering YAMLs:** replace hardcoded paths with `${oc.env:FOUNDRY_ROOT,...}` in all 8 files
4. **`scripts/upload_weights.py`:** upload RFD3 weights + SAE checkpoint + steering vectors to Modal Volume
5. **`modal_worker.py`:** write Modal function with `FOUNDRY_ROOT=/weights`, test with `modal run`
6. **`db.py`:** Supabase CRUD (replaces `store.py`)
7. **`redis_client.py`:** pub/sub helpers
8. **`runner.py`:** swap subprocess → `run_job.spawn`
9. **`main.py`:** wire Redis SSE, Supabase job lookup, signed URL redirect
10. **Delete `store.py`**
11. **Deploy Railway** with new env vars (`SUPABASE_*`, `REDIS_URL`)
12. **Smoke test:** POST /jobs → watch SSE stream → GET /jobs/:id/output

---

## Environment Variables

| Service | Variable | Where used |
|---|---|---|
| Railway | `SUPABASE_URL` | FastAPI + db.py |
| Railway | `SUPABASE_KEY` | FastAPI + db.py |
| Railway | `REDIS_URL` | FastAPI + redis_client.py |
| Modal Secret | `SUPABASE_URL` | modal_worker.py |
| Modal Secret | `SUPABASE_KEY` | modal_worker.py |
| Modal Secret | `REDIS_URL` | modal_worker.py |

---

## File Diff Summary

| File | Action |
|---|---|
| `modal_worker.py` | **New** — Modal GPU function |
| `db.py` | **New** — Supabase job CRUD |
| `redis_client.py` | **New** — Redis pub/sub helpers |
| `scripts/upload_weights.py` | **New** — one-time volume population (RFD3 + SAE + steering vectors) |
| `runner.py` | **Rewrite** — spawn Modal instead of subprocess |
| `main.py` | **Modify** — Redis SSE, signed URL output |
| `models.py` | **Modify** — add output_url, remove logs list |
| `store.py` | **Delete** |
| `sae/configs/steering/ablate_block12_f639*.yaml` (×4) | **Fix** — replace hardcoded paths with `${oc.env:FOUNDRY_ROOT,...}` |
| `sae/configs/steering/rawdiff_neg_block12_c*.yaml` (×4) | **Fix** — replace hardcoded paths with `${oc.env:FOUNDRY_ROOT,...}` |
