"""CLI dispatcher: routes path-steps to their module, rejects upstream steps."""

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


def test_path_step_dispatches_to_its_stub() -> None:
    """A path-invocable step reaches its module's analyze() (still a stub → raises)."""
    with pytest.raises(NotImplementedError):
        main(["stereo_field", "x.wav"])
