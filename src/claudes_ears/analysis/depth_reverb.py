"""Depth / reverb analysis — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Estimate RT60, pre-delay, wetness and perceived distance of the source mix."""
    raise NotImplementedError
