from __future__ import annotations

from typing import TYPE_CHECKING

from claudes_ears.db.library import open_library, upsert_track
from tests.api.conftest import make_doc

if TYPE_CHECKING:
    from pathlib import Path

    import httpx


def _seed(lib_path: Path, count: int) -> None:
    with open_library(lib_path) as con:
        for i in range(count):
            upsert_track(con, make_doc(f"t{i}", title=f"Track {i}", base=0.05 * i))


async def test_library_list_is_paginated(client: httpx.AsyncClient, lib_path: Path) -> None:
    _seed(lib_path, 3)
    body = (await client.get("/library", params={"page": 1, "limit": 2})).json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["page"] == 1
    assert len(body["items"]) == 2


async def test_library_list_empty(client: httpx.AsyncClient, lib_path: Path) -> None:
    _seed(lib_path, 0)
    body = (await client.get("/library")).json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_library_list_rejects_bad_pagination(client: httpx.AsyncClient) -> None:
    assert (await client.get("/library", params={"page": 0})).status_code == 422


async def test_twins_returns_neighbours_excluding_self(
    client: httpx.AsyncClient, lib_path: Path
) -> None:
    _seed(lib_path, 4)
    body = (await client.get("/library/t0/twins", params={"k": 2})).json()
    assert len(body["items"]) == 2
    assert all(item["track_id"] != "t0" for item in body["items"])
    assert body["items"][0]["title"] is not None


async def test_twins_unknown_track_404(client: httpx.AsyncClient, lib_path: Path) -> None:
    _seed(lib_path, 1)
    response = await client.get("/library/ghost/twins")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
