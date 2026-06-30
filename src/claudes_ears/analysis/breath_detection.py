"""Breath detection — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Detect breaths, depth and phrasing in the vocals stem."""
    raise NotImplementedError
