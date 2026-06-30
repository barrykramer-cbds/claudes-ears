"""Frequency-territory interaction between stems — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(stem_dir: Path) -> dict[str, object]:
    """Compute per-band overlap/competition across the separated stems."""
    raise NotImplementedError
