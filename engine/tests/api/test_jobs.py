from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from claudes_ears.api.app import create_app
from tests.api.conftest import lifespan_client

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import httpx

    from claudes_ears.models.jobs import ProgressEvent
    from claudes_ears.models.perception import PerceptionDocument
    from claudes_ears.pipeline.orchestrator import StepResult


async def _wait_terminal(client: httpx.AsyncClient, job_id: str) -> dict[str, object]:
    body: dict[str, object] = {}
    for _ in range(200):
        body = (await client.get(f"/jobs/{job_id}")).json()
        if body["status"] in {"completed", "failed"}:
            return body
        await asyncio.sleep(0.01)
    return body


async def test_job_lifecycle_create_status_perception(
    client: httpx.AsyncClient, audio_file: Path
) -> None:
    created = await client.post("/jobs", json={"audio_path": str(audio_file)})
    assert created.status_code == 201
    assert created.json()["status"] == "queued"
    job_id = created.json()["id"]

    final = await _wait_terminal(client, job_id)
    assert final["status"] == "completed"

    perception = await client.get(f"/jobs/{job_id}/perception")
    assert perception.status_code == 200
    assert perception.json()["track"]["id"] == audio_file.stem


async def test_create_job_rejects_missing_file(client: httpx.AsyncClient) -> None:
    response = await client.post("/jobs", json={"audio_path": "/does/not/exist.wav"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PATH"


async def test_create_job_missing_body_returns_validation_envelope(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/jobs", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


async def test_unknown_job_status_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/jobs/ghost")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_perception_404_until_completed(client: httpx.AsyncClient) -> None:
    assert (await client.get("/jobs/ghost/perception")).status_code == 404


async def test_failed_job_is_reported(audio_file: Path, tmp_path: Path) -> None:
    def boom(
        audio: Path,
        *,
        job_id: str,
        skip_separation: bool,
        progress: Callable[[ProgressEvent], None] | None,
        title: str | None,
        artist: str | None,
    ) -> tuple[PerceptionDocument, dict[str, StepResult | None]]:
        raise RuntimeError("separation exploded")

    app = create_app(
        runner=boom, library_path=tmp_path / "lib.duckdb", work_dir=tmp_path / "work", warm=False
    )
    async with lifespan_client(app) as client:
        job_id = (await client.post("/jobs", json={"audio_path": str(audio_file)})).json()["id"]
        final = await _wait_terminal(client, job_id)
        assert final["status"] == "failed"
        assert final["error"] == "separation exploded"
        assert (await client.get(f"/jobs/{job_id}/perception")).status_code == 404
