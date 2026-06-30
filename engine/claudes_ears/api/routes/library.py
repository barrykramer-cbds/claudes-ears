"""Library index endpoints: paginated track list and VSS sonic-twin lookup."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from claudes_ears.api.app import ApiError, get_state
from claudes_ears.db.library import open_library
from claudes_ears.db.twins import ensure_index, find_twins

if TYPE_CHECKING:
    import duckdb

router = APIRouter(tags=["library"])

_PAGE_SQL = """
SELECT track_id, title, artist, year, genre, era, duration_s, key, mode, tempo,
       ai_verdict, analyzed_at
FROM tracks
ORDER BY analyzed_at DESC NULLS LAST
LIMIT ? OFFSET ?
"""


class TrackSummary(BaseModel):
    track_id: str
    title: str | None = None
    artist: str | None = None
    year: int | None = None
    genre: str | None = None
    era: str | None = None
    duration_s: float | None = None
    key: str | None = None
    mode: str | None = None
    tempo: float | None = None
    ai_verdict: str | None = None
    analyzed_at: datetime | None = None


class TrackPage(BaseModel):
    items: list[TrackSummary]
    total: int
    page: int
    limit: int


class TwinOut(BaseModel):
    track_id: str
    distance: float
    title: str | None = None
    artist: str | None = None


class TwinList(BaseModel):
    items: list[TwinOut]


@router.get("/library", response_model=TrackPage)
async def list_library(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> TrackPage:
    """Return one page of indexed tracks, newest-analyzed first."""
    state = get_state(request)
    offset = (page - 1) * limit
    with open_library(state.library_path) as con:
        count_row = con.execute("SELECT count(*) FROM tracks").fetchone()
        total = int(count_row[0]) if count_row else 0
        rows = con.execute(_PAGE_SQL, [limit, offset]).fetchall()
    items = [
        TrackSummary(
            track_id=str(r[0]),
            title=r[1],
            artist=r[2],
            year=r[3],
            genre=r[4],
            era=r[5],
            duration_s=r[6],
            key=r[7],
            mode=r[8],
            tempo=r[9],
            ai_verdict=r[10],
            analyzed_at=r[11],
        )
        for r in rows
    ]
    return TrackPage(items=items, total=total, page=page, limit=limit)


@router.get("/library/{track_id}/twins", response_model=TwinList)
async def list_twins(
    track_id: str,
    request: Request,
    k: int = Query(10, ge=1, le=100),
) -> TwinList:
    """Return the k nearest sonic twins of an indexed track, nearest first."""
    state = get_state(request)
    with open_library(state.library_path) as con:
        ensure_index(con)
        try:
            twins = find_twins(con, track_id, k=k)
        except KeyError as error:
            raise ApiError(404, "NOT_FOUND", f"no indexed track {track_id!r}") from error
        meta = _twin_meta(con, [t.track_id for t in twins])
    items = [
        TwinOut(
            track_id=t.track_id,
            distance=t.distance,
            title=meta.get(t.track_id, (None, None))[0],
            artist=meta.get(t.track_id, (None, None))[1],
        )
        for t in twins
    ]
    return TwinList(items=items)


def _twin_meta(
    con: duckdb.DuckDBPyConnection, ids: list[str]
) -> dict[str, tuple[str | None, str | None]]:
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    sql = f"SELECT track_id, title, artist FROM tracks WHERE track_id IN ({placeholders})"  # noqa: S608 (placeholders are bound params, ids are parameterized)
    rows = con.execute(sql, ids).fetchall()
    return {str(tid): (title, artist) for tid, title, artist in rows}
