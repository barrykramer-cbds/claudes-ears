"""Library upsert: idempotency, 12-dim vector storage, and emotion-summary derivation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from claudes_ears.db.library import upsert_track
from claudes_ears.models.perception import GenomeVector

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
