"""Vocal register tracking — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Track chest/head/falsetto/fry register across the vocals stem."""
    raise NotImplementedError
