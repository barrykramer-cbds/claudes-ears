"""Embedded DuckDB library index: idempotent upsert of one PerceptionDocument
per track (schema.sql is the frozen DDL; re-analysis updates, never duplicates).
"""

from __future__ import annotations

import contextlib
from importlib import resources
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from claudes_ears.models.perception import PerceptionDocument

_ENERGY_AROUSAL = {"low": 0.0, "medium": 0.5, "mid": 0.5, "high": 1.0}


def _schema_sql() -> str:
    return resources.files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")


def init_db(con: duckdb.DuckDBPyConnection) -> None:
    """Apply the frozen DDL; safe to call repeatedly (all statements are IF NOT EXISTS)."""
    con.execute(_schema_sql())


@contextlib.contextmanager
def open_library(db_path: str | Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open (creating if absent) the library file and apply the schema."""
    con = duckdb.connect(str(db_path))
    try:
        init_db(con)
        yield con
    finally:
        con.close()


def _emotion_summary(doc: PerceptionDocument) -> tuple[float | None, float | None]:
    """Best-effort (valence, arousal): warmth proxies valence, energy label proxies arousal."""
    phases = doc.emotion.phases if doc.emotion else []
    if not phases:
        return None, None
    warmths = [p.avg_warmth for p in phases]
    arousals = [_ENERGY_AROUSAL[e] for p in phases if (e := p.energy.lower()) in _ENERGY_AROUSAL]
    valence = sum(warmths) / len(warmths)
    arousal = sum(arousals) / len(arousals) if arousals else None
    return valence, arousal


def _track_row(doc: PerceptionDocument, perception_path: str | None) -> list[object | None]:
    track = doc.track
    theory = doc.harmony.theory if doc.harmony else None
    chords = doc.harmony.chords if doc.harmony else None
    ai = doc.ai_detection
    valence, arousal = _emotion_summary(doc)
    return [
        track.id,
        track.title,
        track.artist,
        track.year,
        track.genre,
        track.era,
        track.source_path,
        track.duration_s,
        theory.key if theory else None,
        theory.mode if theory else None,
        chords.tempo if chords else None,
        valence,
        arousal,
        ai.verdict if ai else None,
        ai.overall_score if ai else None,
        track.pipeline_version,
        track.analyzed_at,
        perception_path,
    ]


_TRACK_UPSERT = """
INSERT INTO tracks (
  track_id, title, artist, year, genre, era, source_path, duration_s,
  key, mode, tempo, valence, arousal, ai_verdict, ai_score,
  pipeline_version, analyzed_at, perception_path
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (track_id) DO UPDATE SET
  title = excluded.title, artist = excluded.artist, year = excluded.year,
  genre = excluded.genre, era = excluded.era, source_path = excluded.source_path,
  duration_s = excluded.duration_s, key = excluded.key, mode = excluded.mode,
  tempo = excluded.tempo, valence = excluded.valence, arousal = excluded.arousal,
  ai_verdict = excluded.ai_verdict, ai_score = excluded.ai_score,
  pipeline_version = excluded.pipeline_version, analyzed_at = excluded.analyzed_at,
  perception_path = excluded.perception_path
"""

_GENOME_UPSERT = """
INSERT INTO genome_vectors (track_id, vector)
VALUES (?, ?::FLOAT[12])
ON CONFLICT (track_id) DO UPDATE SET vector = excluded.vector
"""


def upsert_track(
    con: duckdb.DuckDBPyConnection,
    doc: PerceptionDocument,
    perception_path: str | None = None,
) -> None:
    """Upsert the track row and (if the doc has a finite genome) its 12-dim vector by track_id."""
    con.execute(_TRACK_UPSERT, _track_row(doc, perception_path))
    if doc.genome is not None:
        con.execute(_GENOME_UPSERT, [doc.track.id, doc.genome.as_list()])
