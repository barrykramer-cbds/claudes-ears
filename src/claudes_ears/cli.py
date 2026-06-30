"""Registry-driven CLI: ``python -m claudes_ears <step> <audio-or-stem-dir>`` runs a
single-path step's analyze(); upstream/library/pair steps defer to the orchestrator.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Protocol, cast

from claudes_ears._sanitize import sanitize
from claudes_ears.pipeline.steps import STEP_BY_NAME, InputKind, Step

#: Input kinds the CLI can supply from a single path argument.
_PATH_INPUTS = frozenset(
    {
        InputKind.AUDIO_FULL,
        InputKind.AUDIO_VOCALS,
        InputKind.AUDIO_DRUMS,
        InputKind.AUDIO_OTHER,
        InputKind.STEM_DIR,
    }
)


class _PathAnalyze(Protocol):
    def __call__(self, path: Path, /) -> dict[str, object]: ...


def _path_invocable(step: Step) -> bool:
    """True if the step takes exactly one path (so the CLI can drive it)."""
    # ai_detector is STEM_DIR but also needs vocal dicts — orchestrator only.
    return step.input in _PATH_INPUTS and step.name != "ai_detector"


def _run_step(step: Step, path: Path) -> dict[str, object]:
    module = importlib.import_module(step.module)
    analyze = cast("_PathAnalyze", module.analyze)
    return analyze(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claudes_ears", description=__doc__)
    parser.add_argument(
        "step",
        choices=sorted(STEP_BY_NAME),
        help="registry step name to run",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="audio file or demucs stem directory the step consumes",
    )
    args = parser.parse_args(argv)

    step = STEP_BY_NAME[args.step]
    if not _path_invocable(step):
        parser.error(
            f"step {step.name!r} consumes upstream data ({step.input.name}); "
            "run it through the orchestrator, not the single-path CLI"
        )

    result = _run_step(step, args.path)
    print(json.dumps(sanitize(result), indent=2))  # noqa: T201 — CLI emits JSON to stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
