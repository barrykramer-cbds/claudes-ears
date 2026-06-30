"""Demucs stem separation (was run_demucs.py) — stub."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def analyze(audio: Path) -> dict[str, object]:
    """Separate ``audio`` into vocals/drums/bass/other under the stem root from config."""
    raise NotImplementedError
