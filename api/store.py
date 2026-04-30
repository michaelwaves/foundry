from api.models import Job

_jobs: dict[str, Job] = {}


def get(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def save(job: Job) -> None:
    _jobs[job.id] = job
