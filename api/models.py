from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


@dataclass
class SteeringConfig:
    feature_id: int
    alpha: float
    apply_at_steps: str = "all"


@dataclass
class JobConfig:
    design_name: str
    diffusion_steps: int = 15
    pdb_storage_path: str | None = None
    contig: str | None = None
    length: str | None = None
    hotspots: dict[str, str] = field(default_factory=dict)
    infer_ori_strategy: str = "hotspots"
    is_non_loopy: bool = True
    partial_t: float = 0.0
    steering: SteeringConfig | None = None


@dataclass
class Job:
    id: str
    status: JobStatus
    error: str | None = None
    output_url: str | None = None
