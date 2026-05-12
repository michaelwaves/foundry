import os
from dataclasses import asdict
from typing import Any

from supabase import Client, create_client

from models import Job, JobConfig, JobStatus


def make_client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def insert_job(db: Client, job_id: str, user_id: str, config: JobConfig) -> None:
    db.table("jobs").insert({
        "id": job_id,
        "status": JobStatus.pending.value,
        "inputs": asdict(config),
        "created_by": user_id,
    }).execute()


def get_job(db: Client, job_id: str, user_id: str) -> Job | None:
    response = (
        db.table("jobs")
        .select("id, status, error, output_url")
        .eq("id", job_id)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    row = rows[0]
    return Job(
        id=row["id"],
        status=JobStatus(row["status"]),
        error=row["error"],
        output_path=row["output_url"],
    )


def update_job(db: Client, job_id: str, **fields: Any) -> None:
    db.table("jobs").update(fields).eq("id", job_id).execute()
