"""Job + progress models for the orchestrator and SSE stream — in-memory only
(one GPU job serializes; no persistence).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(StrEnum):
    """Lifecycle of a single analysis job."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class StepStatus(StrEnum):
    """Per-step transition reported on the progress stream."""

    started = "started"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class ProgressEvent(BaseModel):
    """One SSE payload: a job's position in the ordered pipeline (1-based index)."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    step: str
    index: int = Field(ge=1)
    total: int = Field(ge=1)
    status: StepStatus
    message: str | None = None


class Job(BaseModel):
    """A unit of analysis tracked in the in-memory registry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_path: str
    status: JobStatus = JobStatus.queued
    current_step: str | None = None
    step_index: int = 0
    step_total: int = 0
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
