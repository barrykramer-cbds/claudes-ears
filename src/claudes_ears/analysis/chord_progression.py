"""Chord progression detection — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Detect chord segments and tempo from the source mix."""
    raise NotImplementedError
