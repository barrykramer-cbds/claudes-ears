"""vocal_layers: peak counting, optional echo/dense arrays, degraded input."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from claudes_ears.analysis import vocal_layers as vl
from claudes_ears.models.perception import VocalLayers


def _column(peaks: int, n_bins: int = 24) -> np.ndarray:
    """Build a spectral column with exactly `peaks` isolated bumps above threshold."""
    col = np.zeros(n_bins, dtype=np.float64)
    for j in range(peaks):
        col[1 + j * 2] = 1.0
    return col


def _magnitude(per_frame: list[int], n_bins: int = 24) -> np.ndarray:
    return np.stack([_column(k, n_bins) for k in per_frame], axis=1)


def _fake_librosa(
    *,
    y: np.ndarray,
    duration: float,
    f0: np.ndarray,
    magnitude: np.ndarray,
    freqs: np.ndarray,
    rms: np.ndarray,
    times: np.ndarray,
) -> SimpleNamespace:
    feature = SimpleNamespace(rms=lambda **_: np.asarray([rms]))
    return SimpleNamespace(
        load=lambda *_a, **_k: (y, 22050),
        get_duration=lambda **_k: duration,
        note_to_hz=lambda name: {"C2": 65.4, "C6": 1046.5}[name],
        pyin=lambda *_a, **_k: (f0, None, None),
        stft=lambda *_a, **_k: magnitude,
        fft_frequencies=lambda **_k: freqs,
        feature=feature,
        frames_to_time=lambda _frames, **_k: times,
    )


def _patch(monkeypatch: pytest.MonkeyPatch, fake: SimpleNamespace) -> None:
    monkeypatch.setattr(vl, "librosa", fake)


def test_frame_peak_count_counts_isolated_bumps() -> None:
    assert vl._frame_peak_count(_column(3), vl._PEAK_REL_THRESHOLD) == 3
    assert vl._frame_peak_count(np.zeros(10, dtype=np.float64), vl._PEAK_REL_THRESHOLD) == 0


@pytest.mark.parametrize(
    ("avg", "label"),
    [
        (12.0, "heavily layered (multiple voices)"),
        (8.0, "doubled / harmonized"),
        (5.0, "solo with occasional doubling"),
        (2.0, "solo voice"),
    ],
)
def test_layering_label_thresholds(avg: float, label: str) -> None:
    assert vl._layering_label(avg) == label


def test_detect_echoes_none_when_too_short() -> None:
    rms = np.ones(50, dtype=np.float64)
    assert vl._detect_echoes(rms, 22050) is None


def test_detect_echoes_returns_empty_list_when_no_peaks() -> None:
    rms = np.ones(300, dtype=np.float64)
    echoes = vl._detect_echoes(rms, 22050)
    assert echoes == []


def test_dense_regions_flags_high_density_span() -> None:
    counts = np.asarray([9] * 5 + [2] * 95, dtype=np.int_)
    times = np.arange(len(counts), dtype=np.float64)
    regions, pct = vl._dense_regions(counts, times)
    assert len(regions) == 1
    assert regions[0]["start"] == 0.0
    assert regions[0]["density"] == pytest.approx(9.0)
    assert pct == pytest.approx(5.0)


def test_dense_regions_uniform_has_no_regions() -> None:
    counts = np.asarray([3] * 10, dtype=np.int_)
    times = np.arange(len(counts), dtype=np.float64)
    regions, _pct = vl._dense_regions(counts, times)
    assert regions == []


def test_analyze_happy_path_validates_against_model(monkeypatch: pytest.MonkeyPatch) -> None:
    per_frame = [9] * 5 + [2] * 95
    fake = _fake_librosa(
        y=np.ones(4096, dtype=np.float64),
        duration=12.5,
        f0=np.full(len(per_frame), 220.0),
        magnitude=_magnitude(per_frame),
        freqs=np.linspace(300.0, 3000.0, 24),
        rms=np.ones(300, dtype=np.float64),
        times=np.arange(len(per_frame), dtype=np.float64),
    )
    _patch(monkeypatch, fake)

    result = vl.analyze(Path("vocals.wav"))

    model = VocalLayers.model_validate(result)
    assert model.duration == 12.5
    assert model.dense_regions is not None
    assert len(model.dense_regions) == 1
    assert model.echo_detected is False
    assert model.echoes == []


def test_analyze_short_signal_omits_echo_arrays(monkeypatch: pytest.MonkeyPatch) -> None:
    per_frame = [3] * 8
    fake = _fake_librosa(
        y=np.ones(4096, dtype=np.float64),
        duration=1.0,
        f0=np.full(len(per_frame), 220.0),
        magnitude=_magnitude(per_frame),
        freqs=np.linspace(300.0, 3000.0, 24),
        rms=np.ones(50, dtype=np.float64),
        times=np.arange(len(per_frame), dtype=np.float64),
    )
    _patch(monkeypatch, fake)

    result = vl.analyze(Path("vocals.wav"))

    assert result["echo_detected"] is False
    assert result["echo_desc"] == "insufficient data"
    assert "echoes" not in result
    assert "echo_count" not in result


def test_analyze_empty_input_is_degraded_but_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_librosa(
        y=np.asarray([], dtype=np.float64),
        duration=0.0,
        f0=np.asarray([], dtype=np.float64),
        magnitude=np.zeros((24, 0), dtype=np.float64),
        freqs=np.linspace(300.0, 3000.0, 24),
        rms=np.asarray([], dtype=np.float64),
        times=np.asarray([], dtype=np.float64),
    )
    _patch(monkeypatch, fake)

    result = vl.analyze(Path("silent.wav"))

    model = VocalLayers.model_validate(result)
    assert model.duration == 0.0
    assert model.layering == "solo voice"
    assert model.echo_detected is False
    assert model.dense_regions is None
