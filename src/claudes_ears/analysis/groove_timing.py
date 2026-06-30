"""Groove / micro-timing analysis — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Measure beat deviation, feel, swing and drift from the drums stem."""
    raise NotImplementedError
