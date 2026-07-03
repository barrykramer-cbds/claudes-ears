"""FastAPI sidecar: warms the heavy models once, serializes GPU jobs through a
single worker, and exposes the in-memory job registry to the routers.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from claudes_ears.config import music_dir
from claudes_ears.db.library import open_library, upsert_track
from claudes_ears.download import download_audio
from claudes_ears.models.jobs import Job, JobStatus, ProgressEvent, StepStatus
from claudes_ears.pipeline.orchestrator import StepResult, run_track

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from claudes_ears.models.perception import PerceptionDocument


class RunTrack(Protocol):
    def __call__(
        self,
        audio: Path,
        *,
        job_id: str,
        skip_separation: bool,
        progress: Callable[[ProgressEvent], None] | None,
        title: str | None,
        artist: str | None,
    ) -> tuple[PerceptionDocument, dict[str, StepResult | None]]: ...


class DownloadAudio(Protocol):
    def __call__(
        self, url: str, dest_dir: Path, on_progress: Callable[[str], None] | None = None
    ) -> Path: ...


LIBRARY_ENV = "CLAUDES_EARS_LIBRARY"
WORKDIR_ENV = "CLAUDES_EARS_WORKDIR"
DEFAULT_LIBRARY = Path("./library.duckdb")

logger = logging.getLogger("claudes_ears.api")


class ApiError(Exception):
    """Carries a machine-readable code + HTTP status into the error envelope."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _envelope(status_code: int, code: str, message: str, details: list[object]) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(status_code=status_code, content=body)


@dataclass
class JobSpec:
    skip_separation: bool
    title: str | None
    artist: str | None
    source_url: str | None = None


@dataclass
class JobState:
    job: Job
    spec: JobSpec
    queue: asyncio.Queue[ProgressEvent | None]
    document: PerceptionDocument | None = None


@dataclass
class AppState:
    library_path: Path
    work_dir: Path
    runner: RunTrack = run_track
    downloader: DownloadAudio = download_audio
    warm: bool = True
    jobs: dict[str, JobState] = field(default_factory=dict)
    pending: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    worker_task: asyncio.Task[None] | None = None

    def submit(self, job: Job, spec: JobSpec) -> JobState:
        state = JobState(job=job, spec=spec, queue=asyncio.Queue())
        self.jobs[job.id] = state
        self.pending.put_nowait(job.id)
        return state


def get_state(request: Request) -> AppState:
    state = request.app.state.app_state
    assert isinstance(state, AppState)
    return state


def _now() -> datetime:
    return datetime.now(UTC)


async def _run_job(state: AppState, job_id: str) -> None:
    job_state = state.jobs[job_id]
    job, spec = job_state.job, job_state.spec
    loop = asyncio.get_running_loop()

    def on_progress(event: ProgressEvent) -> None:
        job.current_step = event.step
        job.step_index = event.index
        job.step_total = event.total
        loop.call_soon_threadsafe(job_state.queue.put_nowait, event)

    job.status = JobStatus.running
    try:
        if spec.source_url is not None:
            downloaded = await _download_source(state, job_id, spec.source_url, on_progress)
            job.source_path = str(downloaded)
        document, _ = await asyncio.to_thread(
            state.runner,
            Path(job.source_path),
            job_id=job_id,
            skip_separation=spec.skip_separation,
            progress=on_progress,
            title=spec.title,
            artist=spec.artist,
        )
    except Exception as error:  # a failed analysis must mark the job, not kill the worker
        job.status = JobStatus.failed
        job.error = str(error)
        job.finished_at = _now()
        logger.exception("job %s failed", job_id)
    else:
        job_state.document = document
        _persist(state, document)
        job.status = JobStatus.completed
        job.finished_at = _now()
    finally:
        # through the same threadsafe path as events, so the sentinel never overtakes them
        loop.call_soon_threadsafe(job_state.queue.put_nowait, None)


async def _download_source(
    state: AppState,
    job_id: str,
    url: str,
    on_progress: Callable[[ProgressEvent], None],
) -> Path:
    def emit(step_status: StepStatus, message: str | None) -> None:
        on_progress(
            ProgressEvent(
                job_id=job_id,
                step="download",
                index=1,
                total=1,
                status=step_status,
                message=message,
            )
        )

    emit(StepStatus.started, url)
    try:
        path = await asyncio.to_thread(
            state.downloader,
            url,
            music_dir(),
            lambda percent: emit(StepStatus.started, percent),
        )
    except Exception as error:
        emit(StepStatus.failed, str(error))
        raise
    emit(StepStatus.completed, str(path))
    return path


def _persist(state: AppState, document: PerceptionDocument) -> None:
    perception_dir = state.work_dir / document.track.id
    try:
        perception_dir.mkdir(parents=True, exist_ok=True)
        path = perception_dir / "perception.json"
        path.write_text(document.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        with open_library(state.library_path) as con:
            upsert_track(con, document, str(path))
    except Exception:  # persistence is a side effect; the analysis itself already succeeded
        logger.exception("failed to persist perception for %s", document.track.id)


async def _worker(state: AppState) -> None:
    while True:
        job_id = await state.pending.get()
        try:
            await _run_job(state, job_id)
        finally:
            state.pending.task_done()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    state = get_state_from_app(app)
    if state.warm:
        await asyncio.gather(
            asyncio.to_thread(_warm_separator),
            asyncio.to_thread(_warm_whisper),
        )
    state.worker_task = asyncio.create_task(_worker(state))
    try:
        yield
    finally:
        state.worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await state.worker_task


def get_state_from_app(app: FastAPI) -> AppState:
    state = app.state.app_state
    assert isinstance(state, AppState)
    return state


def _warm_separator() -> None:
    try:
        from claudes_ears.separation.separate import _get_separator

        _get_separator()
    except Exception as error:  # warm-up is opportunistic; a cold start must still boot
        logger.warning("separator warm-up skipped: %s", error)


def _warm_whisper() -> None:
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]  # ships no stubs

        WhisperModel("base")
    except Exception as error:  # warm-up is opportunistic; a cold start must still boot
        logger.warning("whisper warm-up skipped: %s", error)


def _dev_origins() -> list[str]:
    """Browser-dev only: Electron and same-origin callers never send these Origins."""
    ports = os.environ.get("CLAUDES_EARS_DEV_PORTS", "5173")
    return [
        f"http://{host}:{port.strip()}"
        for port in ports.split(",")
        for host in ("localhost", "127.0.0.1")
    ]


def create_app(
    *,
    runner: RunTrack = run_track,
    downloader: DownloadAudio = download_audio,
    library_path: Path | None = None,
    work_dir: Path | None = None,
    warm: bool = True,
) -> FastAPI:
    """Build the sidecar; pass ``warm=False`` and a fake ``runner`` to drive it in tests."""
    resolved_library = library_path or Path(os.environ.get(LIBRARY_ENV, DEFAULT_LIBRARY))
    resolved_work = (
        work_dir or Path(os.environ.get(WORKDIR_ENV, tempfile.gettempdir())) / "claudes-ears-jobs"
    )

    app = FastAPI(title="Claude's Ears", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_dev_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.app_state = AppState(
        library_path=resolved_library,
        work_dir=resolved_work,
        runner=runner,
        downloader=downloader,
        warm=warm,
    )

    from claudes_ears.api import sse
    from claudes_ears.api.routes import jobs, library

    app.include_router(jobs.router)
    app.include_router(sse.router)
    app.include_router(library.router)

    @app.exception_handler(ApiError)
    async def _on_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, exc.message, [])

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = json.loads(json.dumps(exc.errors(), default=str))
        return _envelope(422, "VALIDATION_ERROR", "request validation failed", details)

    return app


app = create_app()
