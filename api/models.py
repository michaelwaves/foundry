from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus = field(default=JobStatus.pending)
    output_path: str | None = None
    error: str | None = None
