"""Shared fixtures for the DuckDB library tests: a temp-file connection and doc builders."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import duckdb
import pytest

from claudes_ears.db.library import init_db
from claudes_ears.models.perception import (
    EmotionPhase,
    EmotionTrajectory,
    GenomeVector,
    PerceptionDocument,
    TrackMeta,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def con(tmp_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    connection = duckdb.connect(str(tmp_path / "library.duckdb"))
    init_db(connection)
    try:
        yield connection
    finally:
        connection.close()


def make_genome(seed: float) -> GenomeVector:
    """A GenomeVector whose 12 dims are all ``seed`` — distance is monotone in |seed_a - seed_b|."""
    return GenomeVector(**dict.fromkeys(GenomeVector.DIMS, seed))


def make_doc(
    track_id: str,
    *,
    genome: GenomeVector | None = None,
    title: str | None = "T",
    with_emotion: bool = False,
) -> PerceptionDocument:
    emotion = None
    if with_emotion:
        emotion = EmotionTrajectory(
            total_windows=1,
            total_transitions=0,
            total_phases=1,
            unique_states=1,
            narrative="n",
            phases=[
                EmotionPhase(
                    state="calm",
                    energy="high",
                    start="0:00",
                    end="0:10",
                    duration_s=10.0,
                    avg_tension=0.2,
                    avg_warmth=0.8,
                )
            ],
        )
    return PerceptionDocument(
        track=TrackMeta(
            id=track_id,
            source_path=f"/music/{track_id}.mp3",
            analyzed_at=datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC),
            pipeline_version="1.0",
            title=title,
        ),
        emotion=emotion,
        genome=genome,
    )
