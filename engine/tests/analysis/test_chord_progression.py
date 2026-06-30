"""chord_progression.analyze: output contract, degraded inputs, segment merging."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np

from claudes_ears.analysis import chord_progression

if TYPE_CHECKING:
    import pytest

_REQUIRED_KEYS = {
    "tempo",
    "total_beats",
    "total_segments",
    "unique_chords",
    "segments",
    "top_patterns",
    "modulations",
    "chord_sequence_summary",
}

_SR = 22050


def _c_major_chroma(n_frames: int) -> np.ndarray:
    """A chromagram that reads strongly as C major across all frames."""
    chroma = np.full((12, n_frames), 0.05, dtype=np.float64)
    for pitch in (0, 4, 7):  # C, E, G
        chroma[pitch, :] = 1.0
    return chroma


def _patch_librosa(
    monkeypatch: pytest.MonkeyPatch,
    *,
    samples: np.ndarray,
    chroma: np.ndarray,
    beat_frames: np.ndarray,
    tempo: float = 120.0,
) -> None:
    """Swap the whole librosa namespace — its lazy beat/feature submodules pull in
    numba, which rejects this env's numpy; a fake keeps the mock at the boundary."""
    fake = SimpleNamespace(
        load=lambda *a, **k: (samples, _SR),
        get_duration=lambda **k: len(samples) / _SR,
        feature=SimpleNamespace(chroma_cqt=lambda **k: chroma),
        beat=SimpleNamespace(beat_track=lambda **k: (np.array([tempo]), beat_frames)),
        frames_to_time=lambda frames, **k: np.asarray(frames, dtype=np.float64) * 0.5,
    )
    monkeypatch.setattr(chord_progression, "librosa", fake)


def test_identify_chord_matches_c_major() -> None:
    frame = _c_major_chroma(1)[:, 0]
    name, confidence = chord_progression._identify_chord(frame)
    assert name == "C"
    assert confidence > 0.9


def test_identify_chord_silence_is_no_chord() -> None:
    name, confidence = chord_progression._identify_chord(np.zeros(12))
    assert name == "N.C."
    assert confidence == 0.0


def test_analyze_emits_full_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    n_frames = 16
    beat_frames = np.arange(0, n_frames, 2)
    _patch_librosa(
        monkeypatch,
        samples=np.ones(_SR * 4, dtype=np.float64),
        chroma=_c_major_chroma(n_frames),
        beat_frames=beat_frames,
    )

    result = chord_progression.analyze(Path("song.mp3"))

    assert set(result) >= _REQUIRED_KEYS
    assert result["tempo"] == 120.0
    assert result["total_beats"] == len(beat_frames)
    segments = result["segments"]
    assert isinstance(segments, list)
    assert segments, "constant C major should produce at least one segment"
    first = segments[0]
    assert first["chord"] == "C"
    assert set(first) == {
        "chord",
        "start",
        "start_beat",
        "end",
        "end_beat",
        "duration_beats",
        "avg_confidence",
    }
    assert first["start_beat"] == 1
    assert first["duration_beats"] == len(beat_frames)


def test_constant_chord_merges_into_single_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    n_frames = 12
    _patch_librosa(
        monkeypatch,
        samples=np.ones(_SR * 3, dtype=np.float64),
        chroma=_c_major_chroma(n_frames),
        beat_frames=np.arange(0, n_frames, 2),
    )
    result = chord_progression.analyze(Path("song.mp3"))
    assert result["total_segments"] == 1
    assert result["unique_chords"] == 1


def test_empty_audio_returns_degraded_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = SimpleNamespace(load=lambda *a, **k: (np.array([], dtype=np.float64), _SR))
    monkeypatch.setattr(chord_progression, "librosa", fake)
    result = chord_progression.analyze(Path("silence.wav"))
    assert set(result) >= _REQUIRED_KEYS
    assert result["tempo"] == 0.0
    assert result["total_beats"] == 0
    assert result["segments"] == []
    assert result["chord_sequence_summary"] == []


def test_no_beats_returns_degraded_with_tempo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_librosa(
        monkeypatch,
        samples=np.ones(_SR, dtype=np.float64),
        chroma=_c_major_chroma(4),
        beat_frames=np.array([], dtype=np.intp),
        tempo=98.0,
    )
    result = chord_progression.analyze(Path("short.wav"))
    assert result["tempo"] == 98.0
    assert result["total_beats"] == 0
    assert result["segments"] == []
