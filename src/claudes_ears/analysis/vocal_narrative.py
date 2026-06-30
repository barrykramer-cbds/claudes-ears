"""Vocal narrative (lead/chorus, call-and-response) — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Segment the vocals into narrative phases and call-response patterns."""
    raise NotImplementedError
