"""htdemucs_ft stem separation via audio-separator (was demucs/run_demucs.py).

Heavy imports (audio_separator) stay function-local so importing this stays cheap
and ml-extra-free; the Separator + model load once and are reused (warm).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import TYPE_CHECKING, Protocol, cast

from claudes_ears import config
from claudes_ears._sanitize import sanitize

if TYPE_CHECKING:

    class _Separator(Protocol):
        output_dir: str

        def load_model(self, model_filename: str) -> None: ...
        def separate(self, audio_file_path: str) -> list[str]: ...


MODEL = "htdemucs_ft.yaml"
MODEL_CACHE_DIR = Path.home() / ".cache" / "claudes-ears" / "separator-models"

CANONICAL_STEMS = frozenset({"vocals", "drums", "bass", "other"})
_STEM_TOKEN = re.compile(r"\(([^)]+)\)")


@lru_cache(maxsize=1)
def _get_separator() -> _Separator:
    """Load htdemucs_ft once; cached so repeated tracks reuse the warm model."""
    from audio_separator.separator import Separator

    separator = Separator(output_dir=".", model_file_dir=str(MODEL_CACHE_DIR))
    separator.load_model(model_filename=MODEL)
    return cast("_Separator", separator)


def _canonical_stem(filename: str) -> str | None:
    """Map an audio-separator output name to its canonical stem via its ``(Stem)`` token."""
    for token in _STEM_TOKEN.findall(filename):
        candidate = str(token).strip().lower()
        if candidate in CANONICAL_STEMS:
            return candidate
    return None


def analyze(audio: Path) -> dict[str, object]:
    """Separate ``audio`` into vocals/drums/bass/other.wav under the config stem root."""
    if not audio.is_file():
        msg = f"Audio file not found: {audio}"
        raise FileNotFoundError(msg)

    stem_dir = config.stems_dir() / audio.stem
    stem_dir.mkdir(parents=True, exist_ok=True)

    separator = _get_separator()
    separator.output_dir = str(stem_dir)
    produced = separator.separate(str(audio))

    present: set[str] = set()
    for name in produced:
        source = Path(name)
        if not source.is_absolute():
            source = stem_dir / source.name
        stem = _canonical_stem(source.name)
        if stem is None:
            continue
        destination = stem_dir / f"{stem}.wav"
        if source != destination:
            source.replace(destination)
        present.add(stem)

    result = {"stems_present": sorted(present), "stem_dir": str(stem_dir)}
    return cast("dict[str, object]", sanitize(result))
