"""Job lifecycle endpoints: submit analysis, poll status, fetch the result document."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from claudes_ears.api.app import ApiError, JobSpec, get_state
from claudes_ears.models.jobs import Job, JobStatus

router = APIRouter(tags=["jobs"])


class JobCreate(BaseModel):
    audio_path: str | None = Field(default=None, min_length=1)
    source_url: str | None = Field(default=None, min_length=1)
    title: str | None = None
    artist: str | None = None
    skip_separation: bool = False


def _resolve_source(body: JobCreate) -> str:
    if (body.audio_path is None) == (body.source_url is None):
        raise ApiError(400, "INVALID_SOURCE", "provide exactly one of audio_path or source_url")
    if body.source_url is not None:
        parsed = urlparse(body.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ApiError(400, "INVALID_SOURCE", "source_url must be an http(s) URL")
        return body.source_url
    audio = Path(body.audio_path or "")
    if not audio.is_file():
        raise ApiError(400, "INVALID_PATH", "audio_path is not an existing file")
    return str(audio)


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=Job)
async def create_job(body: JobCreate, request: Request) -> Job:
    """Validate the source (local path or URL), queue behind the single worker, return it queued."""
    source = _resolve_source(body)
    state = get_state(request)
    job = Job(id=uuid4().hex, source_path=source, created_at=datetime.now(UTC))
    spec = JobSpec(
        skip_separation=body.skip_separation,
        title=body.title,
        artist=body.artist,
        source_url=body.source_url,
    )
    state.submit(job, spec)
    return job


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, request: Request) -> Job:
    """Return the current status of a job."""
    job_state = get_state(request).jobs.get(job_id)
    if job_state is None:
        raise ApiError(404, "NOT_FOUND", f"no job {job_id!r}")
    return job_state.job


@router.get("/jobs/{job_id}/perception")
async def get_perception(job_id: str, request: Request) -> Response:
    """Return the consolidated PerceptionDocument (contract keys); 404 until completed."""
    job_state = get_state(request).jobs.get(job_id)
    if job_state is None:
        raise ApiError(404, "NOT_FOUND", f"no job {job_id!r}")
    if job_state.job.status is not JobStatus.completed or job_state.document is None:
        raise ApiError(404, "NOT_READY", "perception not available until the job completes")
    return Response(
        job_state.document.model_dump_json(by_alias=True),
        media_type="application/json",
    )
