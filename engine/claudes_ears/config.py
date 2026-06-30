"""Single source of truth for env-driven paths (ISSUE-007); resolved lazily so the
environment can be set after import (API lifespan, test fixtures).
"""

from __future__ import annotations

import os
from pathlib import Path

STEMS_ENV = "CLAUDES_EARS_STEMS"
MUSIC_ENV = "CLAUDES_EARS_MUSIC"

DEFAULT_STEMS_DIR = Path("./stems/htdemucs")
DEFAULT_MUSIC_DIR = Path("./music")


def stems_dir() -> Path:
    """Return the demucs stem-output root (``CLAUDES_EARS_STEMS`` or the default)."""
    raw = os.environ.get(STEMS_ENV)
    return Path(raw) if raw else DEFAULT_STEMS_DIR


def music_dir() -> Path:
    """Return the source-audio library root (``CLAUDES_EARS_MUSIC`` or the default)."""
    raw = os.environ.get(MUSIC_ENV)
    return Path(raw) if raw else DEFAULT_MUSIC_DIR
