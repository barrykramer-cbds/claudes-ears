"""SSE progress stream: bridges a job's worker-thread ``ProgressEvent``s (queued
via the event loop) to the client until the terminal sentinel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from claudes_ears.api.app import ApiError, get_state

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request) -> EventSourceResponse:
    """Stream ordered ProgressEvents for a job; closes once the pipeline terminates."""
    state = get_state(request)
    job_state = state.jobs.get(job_id)
    if job_state is None:
        raise ApiError(404, "NOT_FOUND", f"no job {job_id!r}")

    async def stream() -> AsyncIterator[dict[str, str]]:
        queue = job_state.queue
        while True:
            if await request.is_disconnected():
                break
            event = await queue.get()
            if event is None:
                break
            yield {"event": "progress", "data": event.model_dump_json()}

    return EventSourceResponse(stream())
