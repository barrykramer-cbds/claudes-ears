"""VSS twin search over genome_vectors: HNSW index + nearest-neighbour lookup.

Distance is L2 (``array_distance``) over the 12-dim GenomeVector — smaller is more alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from claudes_ears.models.perception import GenomeVector

if TYPE_CHECKING:
    import duckdb

_DIM = len(GenomeVector.DIMS)


@dataclass(frozen=True)
class Twin:
    track_id: str
    distance: float


def ensure_index(con: duckdb.DuckDBPyConnection) -> None:
    """Load VSS and (re)create the persistent HNSW index on genome_vectors.vector."""
    con.execute("INSTALL vss")
    con.execute("LOAD vss")
    con.execute("SET hnsw_enable_experimental_persistence = true")
    con.execute("CREATE INDEX IF NOT EXISTS genome_hnsw ON genome_vectors USING HNSW (vector)")


def find_twins_by_vector(
    con: duckdb.DuckDBPyConnection,
    vector: list[float],
    k: int = 10,
    exclude: str | None = None,
) -> list[Twin]:
    """Return the k nearest tracks to a raw 12-dim vector, ranked nearest first."""
    if len(vector) != _DIM:
        raise ValueError(f"vector must have {_DIM} dims, got {len(vector)}")
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    # HNSW pushes LIMIT into the index scan, so filter excluded ids AFTER fetching k+1
    # — an in-SQL WHERE would silently shrink the result below k.
    fetch = k + 1 if exclude is not None else k
    rows = con.execute(
        f"SELECT track_id, array_distance(vector, ?::FLOAT[{_DIM}]) AS d "  # noqa: S608 (_DIM is an internal constant)
        "FROM genome_vectors ORDER BY d LIMIT ?",
        [vector, fetch],
    ).fetchall()
    twins = [Twin(track_id=str(tid), distance=float(d)) for tid, d in rows if tid != exclude]
    return twins[:k]


def find_twins(con: duckdb.DuckDBPyConnection, track_id: str, k: int = 10) -> list[Twin]:
    """Return the k nearest tracks to an indexed track, excluding the track itself."""
    row = con.execute("SELECT vector FROM genome_vectors WHERE track_id = ?", [track_id]).fetchone()
    if row is None:
        raise KeyError(f"no genome vector for track_id {track_id!r}")
    return find_twins_by_vector(con, [float(x) for x in row[0]], k=k, exclude=track_id)
