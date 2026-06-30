"""Vocal harmonic-interval analysis — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Profile melodic/harmonic intervals and consonance in the vocals stem."""
    raise NotImplementedError
