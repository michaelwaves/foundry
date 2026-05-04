import uuid
from dataclasses import asdict

import modal
from supabase import Client

from db import insert_job
from models import JobConfig

_run_job = modal.Function.from_name("foundry", "run_job")


def submit_job(db: Client, user_id: str, config: JobConfig) -> str:
    job_id = str(uuid.uuid4())
    insert_job(db, job_id, user_id, config)
    _run_job.spawn(job_id, user_id, asdict(config))
    return job_id
