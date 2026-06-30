"""Structural AI detection — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(stem_dir: Path, vocal_outputs: dict[str, object]) -> dict[str, object]:
    """Score self-opposition vs self-agreement from stem dir + vocal-analysis dicts.

    ``vocal_outputs`` is keyed by depends_on step name.
    """
    raise NotImplementedError
