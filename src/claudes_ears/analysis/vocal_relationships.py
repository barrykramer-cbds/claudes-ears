"""Vocal relationship taxonomy over time — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Label moment-to-moment vocal relationships (solo..withdraw) in the vocals stem."""
    raise NotImplementedError
