"""Frequency interaction: pairwise overlap shape, the <2-stem territory guard.

librosa lives in the optional ``ml`` extra, absent from the test env, so it is
faked at the import boundary with a numpy STFT and a tone registry.
"""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from pathlib import Path

_SR = 22050
_N_FFT = 2048
_signals: dict[str, np.ndarray] = {}


def _fake_load(path: object, sr: int = _SR, mono: bool = True) -> tuple[np.ndarray, int]:
    from pathlib import Path

    return _signals[Path(str(path)).name], sr


def _fake_stft(y: np.ndarray, n_fft: int = _N_FFT) -> np.ndarray:
    hop = n_fft // 4
    win = np.hanning(n_fft)
    n_frames = 1 + max(0, (len(y) - n_fft) // hop)
    out = np.empty((n_fft // 2 + 1, n_frames), dtype=complex)
    for i in range(n_frames):
        out[:, i] = np.fft.rfft(y[i * hop : i * hop + n_fft] * win)
    return out


def _fake_fft_frequencies(sr: int = _SR, n_fft: int = _N_FFT) -> np.ndarray:
    return np.fft.rfftfreq(n_fft, d=1.0 / sr)


@pytest.fixture(autouse=True)
def _fake_librosa() -> None:
    module = types.ModuleType("librosa")
    module.load = _fake_load  # type: ignore[attr-defined]
    module.stft = _fake_stft  # type: ignore[attr-defined]
    module.fft_frequencies = _fake_fft_frequencies  # type: ignore[attr-defined]
    sys.modules["librosa"] = module
    _signals.clear()


def _write_tone(path: Path, freq: float, seconds: float = 1.0) -> None:
    path.touch()
    t = np.linspace(0, seconds, int(_SR * seconds), endpoint=False)
    _signals[path.name] = 0.5 * np.sin(2 * np.pi * freq * t)


def test_two_stems_produce_pairs_and_territory(tmp_path: Path) -> None:
    from claudes_ears.analysis.freq_interaction import analyze

    _write_tone(tmp_path / "bass.wav", 100.0)
    _write_tone(tmp_path / "vocals.wav", 1000.0)

    result = analyze(tmp_path)

    assert result["stem_count"] == 2
    pairs = result["pairs"]
    assert isinstance(pairs, list)
    assert len(pairs) == 1
    pair = pairs[0]
    assert set(pair) == {"pair", "bands", "overall_overlap", "competition"}
    assert result["territory"] != {}


def test_dominant_stem_owns_its_band(tmp_path: Path) -> None:
    from claudes_ears.analysis.freq_interaction import analyze

    _write_tone(tmp_path / "bass.wav", 100.0)
    _write_tone(tmp_path / "vocals.wav", 1000.0)

    territory = analyze(tmp_path)["territory"]
    assert isinstance(territory, dict)
    # The 100 Hz tone must own the bass band; the 1 kHz tone the mid band.
    assert max(territory["bass"], key=territory["bass"].get) == "bass"
    assert max(territory["mid"], key=territory["mid"].get) == "vocals"


def test_single_stem_yields_empty_territory(tmp_path: Path) -> None:
    from claudes_ears.analysis.freq_interaction import analyze

    _write_tone(tmp_path / "vocals.wav", 440.0)

    result = analyze(tmp_path)

    assert result["stem_count"] == 1
    assert result["pairs"] == []
    assert result["territory"] == {}


def test_empty_directory_yields_empty_territory(tmp_path: Path) -> None:
    from claudes_ears.analysis.freq_interaction import analyze

    result = analyze(tmp_path)

    assert result["stem_count"] == 0
    assert result["pairs"] == []
    assert result["territory"] == {}
