from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.models import JobStatus
from api.runner import JOBS_DIR, create_job, launch
from api.store import get


@asynccontextmanager
async def lifespan(app: FastAPI):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/jobs")
async def submit_job(
    background_tasks: BackgroundTasks,
    alpha: float = Form(...),
    motif: UploadFile | None = File(None),
):
    motif_bytes = await motif.read() if motif else None
    job = create_job()
    background_tasks.add_task(launch, job, alpha, motif_bytes)
    return {"job_id": job.id}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"status": job.status, "error": job.error}


@app.get("/jobs/{job_id}/output")
async def get_job_output(job_id: str):
    job = get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.done:
        raise HTTPException(status_code=400, detail=f"job not done (status: {job.status})")
    return FileResponse(
        job.output_path,
        filename="output.cif.gz",
        media_type="application/gzip",
    )
