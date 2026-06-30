from __future__ import annotations

from typing import TYPE_CHECKING

from tests.api.conftest import STEPS

if TYPE_CHECKING:
    from pathlib import Path

    import httpx


async def test_sse_streams_one_event_per_step(client: httpx.AsyncClient, audio_file: Path) -> None:
    job_id = (await client.post("/jobs", json={"audio_path": str(audio_file)})).json()["id"]

    data_lines: list[str] = []
    async with client.stream("GET", f"/jobs/{job_id}/events") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                data_lines.append(line)

    assert len(data_lines) == len(STEPS)
    assert STEPS[0] in data_lines[0]
    assert STEPS[-1] in data_lines[-1]


async def test_sse_unknown_job_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/jobs/ghost/events")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
