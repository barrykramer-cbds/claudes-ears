"""Temporal segmentation — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Snapshot the source mix over time and summarize its structural arc."""
    raise NotImplementedError
