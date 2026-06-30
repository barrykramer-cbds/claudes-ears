"""analyze_stems: stem discovery, genome-field types, int/float coercion, sanitize."""

from pathlib import Path

import numpy as np
import pytest

from claudes_ears.analysis import analyze_stems
from claudes_ears.analysis.analyze_stems import (
    _analyze_drums,
    _analyze_vocals,
    _melodic_entropy,
    analyze,
)

_SR = 22050


def _tone(freq: float = 220.0, dur: float = 0.5) -> np.ndarray:
    t = np.linspace(0, dur, int(_SR * dur), endpoint=False, dtype=np.float32)
    wave: np.ndarray = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return wave


def _harmonic_tone(freq: float = 110.0, dur: float = 3.0) -> np.ndarray:
    """A multi-harmonic, multi-second tone — long enough for chroma_cqt's octave
    decimation and rich enough for tuning estimation, so librosa stays quiet."""
    t = np.linspace(0, dur, int(_SR * dur), endpoint=False, dtype=np.float32)
    wave = np.zeros(int(_SR * dur), dtype=np.float32)
    for k in (1, 2, 3, 4):
        wave += (0.5 / k * np.sin(2 * np.pi * freq * k * t)).astype(np.float32)
    return wave


def _silence(dur: float = 0.5) -> np.ndarray:
    return np.zeros(int(_SR * dur), dtype=np.float32)


def test_empty_stem_dir_returns_empty(tmp_path: Path) -> None:
    assert analyze(tmp_path) == {}


def test_only_present_stems_are_analyzed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "vocals.wav").touch()
    (tmp_path / "drums.wav").touch()
    monkeypatch.setattr(analyze_stems, "_load", lambda _p: (_tone(), _SR))

    result = analyze(tmp_path)

    assert set(result) == {"vocals", "drums"}


def test_mp3_fallback_extension_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "bass.mp3").touch()
    monkeypatch.setattr(analyze_stems, "_load", lambda _p: (_harmonic_tone(), _SR))

    result = analyze(tmp_path)

    assert set(result) == {"bass"}


def test_vocals_genome_fields_are_floats() -> None:
    result = _analyze_vocals(_tone(220.0), _SR)

    for field in ("pitch_mean_hz", "pitch_range_semitones", "voiced_fraction", "breathiness"):
        assert isinstance(result[field], float), field


def test_dynamic_range_fallback_is_float_not_int() -> None:
    result = _analyze_vocals(_silence(), _SR)

    assert result["dynamic_range_db"] == 0.0
    assert isinstance(result["dynamic_range_db"], float)


def test_melodic_entropy_empty_transitions_is_float_zero() -> None:
    value = _melodic_entropy(np.array([440.0], dtype=np.float32))

    assert value == 0.0
    assert isinstance(value, float)


def test_kit_balance_percentages_are_floats_summing_to_100() -> None:
    result = _analyze_drums(_tone(120.0), _SR)
    balance = result["kit_balance"]

    assert isinstance(balance, dict)
    assert all(isinstance(v, float) for v in balance.values())
    assert sum(balance.values()) == pytest.approx(100.0, abs=0.5)


def test_analyze_nulls_non_finite_via_sanitize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "vocals.wav").touch()
    monkeypatch.setattr(analyze_stems, "_load", lambda _p: (_silence(), _SR))
    monkeypatch.setitem(
        analyze_stems._ANALYZERS, "vocals", lambda _y, _sr: {"breathiness": float("inf")}
    )

    vocals = analyze(tmp_path)["vocals"]

    assert isinstance(vocals, dict)
    assert vocals["breathiness"] is None
