"""VSS twin search: ordering by genome distance, self-exclusion, and input guards."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from claudes_ears.db.library import upsert_track
from claudes_ears.db.twins import ensure_index, find_twins, find_twins_by_vector

from .conftest import make_doc, make_genome

if TYPE_CHECKING:
    import duckdb


def _seed(con: duckdb.DuckDBPyConnection, seeds: dict[str, float]) -> None:
    for tid, s in seeds.items():
        upsert_track(con, make_doc(tid, genome=make_genome(s)))
    ensure_index(con)


def test_twins_ranked_nearest_first(con: duckdb.DuckDBPyConnection) -> None:
    _seed(con, {"a": 0.0, "near": 1.0, "mid": 5.0, "far": 50.0})
    twins = find_twins(con, "a", k=3)
    assert [t.track_id for t in twins] == ["near", "mid", "far"]
    assert twins[0].distance < twins[1].distance < twins[2].distance


def test_find_twins_excludes_self(con: duckdb.DuckDBPyConnection) -> None:
    _seed(con, {"a": 0.0, "b": 1.0})
    twins = find_twins(con, "a", k=10)
    assert "a" not in {t.track_id for t in twins}


def test_find_twins_unknown_track_raises(con: duckdb.DuckDBPyConnection) -> None:
    _seed(con, {"a": 0.0})
    with pytest.raises(KeyError):
        find_twins(con, "ghost")


def test_find_twins_by_vector_wrong_dims_raises(con: duckdb.DuckDBPyConnection) -> None:
    _seed(con, {"a": 0.0})
    with pytest.raises(ValueError, match="12 dims"):
        find_twins_by_vector(con, [1.0, 2.0, 3.0])


def test_find_twins_by_vector_bad_k_raises(con: duckdb.DuckDBPyConnection) -> None:
    _seed(con, {"a": 0.0})
    with pytest.raises(ValueError, match="k must be"):
        find_twins_by_vector(con, [1.0] * 12, k=0)


def test_index_is_idempotent(con: duckdb.DuckDBPyConnection) -> None:
    _seed(con, {"a": 0.0, "b": 1.0})
    ensure_index(con)  # second call must not raise
    twins = find_twins(con, "a", k=1)
    assert twins[0].track_id == "b"
