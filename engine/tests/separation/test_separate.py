"""Behavior of the audio-separator separation step with the model boundary mocked."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from claudes_ears import config
from claudes_ears.separation import separate

if TYPE_CHECKING:
    from collections.abc import Iterable


class _FakeSeparator:
    """Stand-in for audio_separator's Separator: writes htdemucs_ft-style stem files."""

    def __init__(self, stem_labels: Iterable[str]) -> None:
        self._stem_labels = list(stem_labels)
        self.output_dir = "."

    def separate(self, audio_file_path: str) -> list[str]:
        track = Path(audio_file_path).stem
        produced: list[str] = []
        for label in self._stem_labels:
            path = Path(self.output_dir) / f"{track}_({label})_htdemucs_ft.wav"
            path.write_bytes(b"wav")
            produced.append(str(path))
        return produced


@pytest.fixture
def source_audio(tmp_path: Path) -> Path:
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"not really audio")
    return audio


def _install_separator(monkeypatch: pytest.MonkeyPatch, stem_labels: Iterable[str]) -> MagicMock:
    factory = MagicMock(return_value=_FakeSeparator(stem_labels))
    monkeypatch.setattr(separate, "_get_separator", factory)
    return factory


def test_returns_present_stems_and_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_audio: Path
) -> None:
    monkeypatch.setenv(config.STEMS_ENV, str(tmp_path / "stems"))
    _install_separator(monkeypatch, ["Vocals", "Drums"])

    result = separate.analyze(source_audio)

    stem_dir = tmp_path / "stems" / "song"
    assert result == {"stems_present": ["drums", "vocals"], "stem_dir": str(stem_dir)}
    assert (stem_dir / "vocals.wav").is_file()
    assert (stem_dir / "drums.wav").is_file()


def test_honors_config_stem_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_audio: Path
) -> None:
    custom_root = tmp_path / "elsewhere" / "htdemucs"
    monkeypatch.setenv(config.STEMS_ENV, str(custom_root))
    _install_separator(monkeypatch, ["Vocals"])

    result = separate.analyze(source_audio)

    stem_dir = custom_root / "song"
    assert result["stem_dir"] == str(stem_dir)
    assert (stem_dir / "vocals.wav").is_file()


def test_produces_four_canonical_filenames(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_audio: Path
) -> None:
    monkeypatch.setenv(config.STEMS_ENV, str(tmp_path / "stems"))
    _install_separator(monkeypatch, ["Vocals", "Drums", "Bass", "Other"])

    result = separate.analyze(source_audio)

    stem_dir = tmp_path / "stems" / "song"
    assert result["stems_present"] == ["bass", "drums", "other", "vocals"]
    assert {p.name for p in stem_dir.glob("*.wav")} == {
        "vocals.wav",
        "drums.wav",
        "bass.wav",
        "other.wav",
    }


def test_track_name_with_parens_resolves_real_stem(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.STEMS_ENV, str(tmp_path / "stems"))
    audio = tmp_path / "song (live).mp3"
    audio.write_bytes(b"x")
    _install_separator(monkeypatch, ["Vocals"])

    result = separate.analyze(audio)

    assert result["stems_present"] == ["vocals"]


def test_missing_audio_raises_without_loading_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    factory = _install_separator(monkeypatch, ["Vocals"])

    with pytest.raises(FileNotFoundError):
        separate.analyze(tmp_path / "absent.mp3")

    factory.assert_not_called()


def test_separation_failure_propagates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_audio: Path
) -> None:
    monkeypatch.setenv(config.STEMS_ENV, str(tmp_path / "stems"))
    sep = MagicMock()
    sep.separate.side_effect = RuntimeError("cuda oom")
    monkeypatch.setattr(separate, "_get_separator", lambda: sep)

    with pytest.raises(RuntimeError, match="cuda oom"):
        separate.analyze(source_audio)

    stem_dir = tmp_path / "stems" / "song"
    assert list(stem_dir.glob("*.wav")) == []


def test_get_separator_is_warm_cached() -> None:
    assert hasattr(separate._get_separator, "cache_clear")
