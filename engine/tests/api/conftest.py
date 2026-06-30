from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from httpx import ASGITransport
import pytest

from claudes_ears.api.app import create_app
from claudes_ears.models.jobs import ProgressEvent, StepStatus
from claudes_ears.models.perception import GenomeVector, PerceptionDocument, TrackMeta

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from pathlib import Path

    from fastapi import FastAPI

    from claudes_ears.pipeline.orchestrator import StepResult

STEPS = ("separation", "analyze_stems", "music_theory")


def make_doc(
    track_id: str, *, title: str | None = None, base: float | None = None
) -> PerceptionDocument:
    genome = None
    if base is not None:
        genome = GenomeVector(**{dim: base + i * 0.01 for i, dim in enumerate(GenomeVector.DIMS)})
    return PerceptionDocument(
        track=TrackMeta(
            id=track_id,
            title=title,
            source_path=f"/music/{track_id}.wav",
            analyzed_at=datetime.now(UTC),
            pipeline_version="test",
        ),
        genome=genome,
    )


def fake_runner(
    audio: Path,
    *,
    job_id: str,
    skip_separation: bool,
    progress: Callable[[ProgressEvent], None] | None,
    title: str | None,
    artist: str | None,
) -> tuple[PerceptionDocument, dict[str, StepResult | None]]:
    for index, name in enumerate(STEPS, start=1):
        if progress is not None:
            progress(
                ProgressEvent(
                    job_id=job_id,
                    step=name,
                    index=index,
                    total=len(STEPS),
                    status=StepStatus.completed,
                )
            )
    return make_doc(audio.stem, title=title), {}


@contextlib.asynccontextmanager
async def lifespan_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Drive the app's lifespan (warm + worker) around an httpx ASGI client."""
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


@pytest.fixture
def lib_path(tmp_path: Path) -> Path:
    return tmp_path / "library.duckdb"


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "song.wav"
    path.write_bytes(b"RIFF0000WAVE")
    return path


@pytest.fixture
async def client(tmp_path: Path, lib_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        runner=fake_runner, library_path=lib_path, work_dir=tmp_path / "work", warm=False
    )
    async with lifespan_client(app) as test_client:
        yield test_client
