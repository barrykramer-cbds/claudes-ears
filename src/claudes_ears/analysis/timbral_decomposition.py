"""NMF timbral component decomposition — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Decompose the 'other' stem into timbral components (bound n_components)."""
    raise NotImplementedError
