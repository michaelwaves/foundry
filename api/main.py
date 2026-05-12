import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from auth import get_user_id
from db import get_job, make_client
from worker_output import make_fresh_signed_url
from models import JobConfig, JobStatus
from redis_client import channel_for, make_redis
from runner import submit_job

import os
_db = None
_redis = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db, _redis
    _db = make_client()
    _redis = make_redis()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs")
def create_job(config: JobConfig, user_id: str = Depends(get_user_id)) -> dict[str, str]:
    job_id = submit_job(_db, user_id, config)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def read_job(job_id: str, user_id: str = Depends(get_user_id)) -> dict:
    job = get_job(_db, job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"status": job.status.value, "error": job.error}


@app.get("/jobs/{job_id}/stream")
def stream_job(job_id: str, user_id: str = Depends(get_user_id)) -> StreamingResponse:
    if not get_job(_db, job_id, user_id):
        raise HTTPException(status_code=404)
    return StreamingResponse(
        _job_event_stream(job_id, user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/jobs/{job_id}/output")
def read_output(job_id: str, user_id: str = Depends(get_user_id)) -> RedirectResponse:
    job = get_job(_db, job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.done or not job.output_path:
        raise HTTPException(
            status_code=400, detail=f"job not done (status: {job.status.value})")
    return RedirectResponse(make_fresh_signed_url(_db, job.output_path), status_code=307)


async def _job_event_stream(job_id: str, user_id: str) -> AsyncGenerator[str, None]:
    pubsub = _redis.pubsub()
    pubsub.subscribe(channel_for(job_id))
    job = get_job(_db, job_id, user_id)
    if job:
        yield _format_status_event(job.status.value, job.error)
        if job.status in (JobStatus.done, JobStatus.failed):
            return
    try:
        while True:
            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0, ignore_subscribe_messages=True)
            if not message:
                continue
            data = message["data"]
            if data.startswith("__done__"):
                return
            yield _decode_redis_event(data)
    finally:
        pubsub.close()


def _decode_redis_event(raw: str) -> str:
    event_type, _, payload = raw.partition("\x1f")
    if event_type == "log":
        return _format_event("log", payload)
    if event_type == "status":
        status, _, error = payload.partition("\x1e")
        return _format_status_event(status, error or None)
    return ""


def _format_status_event(status: str, error: str | None) -> str:
    return _format_event("status", json.dumps({"status": status, "error": error}))


def _format_event(event_type: str, data: str) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data) if event_type == 'log' else data}\n\n"
