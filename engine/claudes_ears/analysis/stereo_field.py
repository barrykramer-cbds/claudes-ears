"""Stereo-field analysis — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Measure width, balance and correlation of the source mix (mono-safe)."""
    raise NotImplementedError
