"""CLI dispatcher: routes path-steps to their module, rejects upstream steps."""

from pathlib import Path

import pytest

from claudes_ears.cli import main


def test_upstream_step_is_rejected_with_a_clear_error() -> None:
    """A derived (upstream-dict) step can't be driven from one path → exit 2."""
    with pytest.raises(SystemExit) as exc:
        main(["music_theory", "ignored"])
    assert exc.value.code == 2  # argparse usage error


def test_unknown_step_is_rejected() -> None:
    with pytest.raises(SystemExit):
        main(["not_a_step", "x.wav"])


def test_path_step_dispatches_to_its_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """A path-invocable step reaches its module's analyze() with the given path."""
    from claudes_ears.analysis import stereo_field

    seen: dict[str, Path] = {}

    def fake_analyze(path: Path) -> dict[str, object]:
        seen["path"] = path
        return {"ok": True}

    monkeypatch.setattr(stereo_field, "analyze", fake_analyze)
    assert main(["stereo_field", "x.wav"]) == 0
    assert seen["path"] == Path("x.wav")
