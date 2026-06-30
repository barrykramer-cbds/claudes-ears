"""Library upsert: idempotency, 12-dim vector storage, emotion summary, and metadata query."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from claudes_ears.db.library import get_track_metadata, upsert_track
from claudes_ears.models.perception import GenomeVector, PerceptionDocument, TrackMeta

from .conftest import make_doc, make_genome

if TYPE_CHECKING:
    import duckdb


def test_reanalysis_does_not_duplicate_rows(con: duckdb.DuckDBPyConnection) -> None:
    doc = make_doc("song-a", genome=make_genome(1.0))
    upsert_track(con, doc)
    upsert_track(con, doc)
    upsert_track(con, doc)
    assert con.execute("SELECT count(*) FROM tracks").fetchone() == (1,)
    assert con.execute("SELECT count(*) FROM genome_vectors").fetchone() == (1,)


def test_upsert_updates_mutable_columns(con: duckdb.DuckDBPyConnection) -> None:
    upsert_track(con, make_doc("song-a", title="Old", genome=make_genome(1.0)))
    upsert_track(con, make_doc("song-a", title="New", genome=make_genome(2.0)))
    title = con.execute("SELECT title FROM tracks WHERE track_id = ?", ["song-a"]).fetchone()
    assert title == ("New",)
    vec = con.execute("SELECT vector FROM genome_vectors WHERE track_id = ?", ["song-a"]).fetchone()
    assert vec is not None
    assert vec[0] == pytest.approx([2.0] * 12)


def test_genome_stored_in_canonical_dim_order(con: duckdb.DuckDBPyConnection) -> None:
    genome = GenomeVector(**{dim: float(i) for i, dim in enumerate(GenomeVector.DIMS)})
    upsert_track(con, make_doc("song-a", genome=genome))
    vec = con.execute("SELECT vector FROM genome_vectors WHERE track_id = ?", ["song-a"]).fetchone()
    assert vec is not None
    assert vec[0] == pytest.approx(list(range(12)))


def test_missing_genome_writes_track_but_no_vector(con: duckdb.DuckDBPyConnection) -> None:
    upsert_track(con, make_doc("song-a", genome=None))
    assert con.execute("SELECT count(*) FROM tracks").fetchone() == (1,)
    assert con.execute("SELECT count(*) FROM genome_vectors").fetchone() == (0,)


def test_emotion_summary_derived(con: duckdb.DuckDBPyConnection) -> None:
    upsert_track(con, make_doc("song-a", with_emotion=True))
    row = con.execute(
        "SELECT valence, arousal FROM tracks WHERE track_id = ?", ["song-a"]
    ).fetchone()
    assert row == pytest.approx((0.8, 1.0))


def test_emotion_summary_null_without_emotion(con: duckdb.DuckDBPyConnection) -> None:
    upsert_track(con, make_doc("song-a"))
    row = con.execute(
        "SELECT valence, arousal FROM tracks WHERE track_id = ?", ["song-a"]
    ).fetchone()
    assert row == (None, None)


def _make_doc_with_metadata(
    track_id: str,
    *,
    year: int | None = None,
    era: str | None = None,
    artist: str | None = None,
    genre: str | None = None,
) -> PerceptionDocument:
    return PerceptionDocument(
        track=TrackMeta(
            id=track_id,
            source_path=f"/music/{track_id}.mp3",
            analyzed_at=datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC),
            pipeline_version="1.0",
            year=year,
            era=era,
            artist=artist,
            genre=genre,
        )
    )


def test_metadata_round_trip(con: duckdb.DuckDBPyConnection) -> None:
    doc = _make_doc_with_metadata(
        "classic-a", year=1971, era="golden-age", artist="Marvin Gaye", genre="soul"
    )
    upsert_track(con, doc)
    meta = get_track_metadata(con, "classic-a")
    assert meta is not None
    assert meta.year == 1971
    assert meta.era == "golden-age"
    assert meta.artist == "Marvin Gaye"
    assert meta.genre == "soul"


def test_metadata_null_fields_preserved(con: duckdb.DuckDBPyConnection) -> None:
    # Tracks with no metadata still return a result, all fields None.
    upsert_track(con, make_doc("no-meta"))
    meta = get_track_metadata(con, "no-meta")
    assert meta is not None
    assert meta.year is None
    assert meta.era is None
    assert meta.artist is None
    assert meta.genre is None


def test_metadata_unknown_track_returns_none(con: duckdb.DuckDBPyConnection) -> None:
    meta = get_track_metadata(con, "ghost-track")
    assert meta is None


def test_metadata_updated_on_reanalysis(con: duckdb.DuckDBPyConnection) -> None:
    upsert_track(con, _make_doc_with_metadata("song-x", year=1965, genre="blues"))
    upsert_track(con, _make_doc_with_metadata("song-x", year=1970, genre="soul"))
    meta = get_track_metadata(con, "song-x")
    assert meta is not None
    assert meta.year == 1970
    assert meta.genre == "soul"
