"""Vocal layering + echo detection — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Detect harmonic layering and echo structure in the vocals stem."""
    raise NotImplementedError
