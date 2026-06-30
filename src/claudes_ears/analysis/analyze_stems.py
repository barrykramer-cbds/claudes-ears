"""Per-stem feature extraction — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(stem_dir: Path) -> dict[str, object]:
    """Emit the per-stem dict that feeds the 12-dim genome vector."""
    raise NotImplementedError
