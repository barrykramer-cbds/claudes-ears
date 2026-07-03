# ISSUE-015: audio_separator missing from mypy ignore_missing_imports override

**Severity**: LOW
**Type**: Technical Debt
**Discovered By**: python-engineer
**Discovered During**: ad-hoc (separate.py demucs -> audio-separator runner swap)
**Affected Files**: engine/pyproject.toml, engine/claudes_ears/separation/separate.py
**Assigned To**: unassigned
**Status**: Closed

---

## Description

`separate.py` now imports `audio_separator.separator.Separator` (function-local). The
`[[tool.mypy.overrides]]` block in `engine/pyproject.toml` lists the old `demucs.*` module
for `ignore_missing_imports` but not `audio_separator.*`. `audio_separator` ships no type
stubs, so once the `ml` extra is synced, strict mypy reports `import-untyped` on that import.

To keep mypy green right now (core env, package not installed) the import carries
`# type: ignore[import-not-found]  # ml-only` in `separate.py:36`.

## Reproduction / Evidence

`cd engine && uv sync --extra ml && uv run mypy claudes_ears/separation/separate.py`
-> the `[import-not-found]` ignore becomes `[unused-ignore]` and an `import-untyped` error
surfaces, because with the package present the error code changes.

## Impact

The current `# type: ignore` is correct only while the package is absent. After an `ml`
sync the suppression breaks mypy. Dual behavior is a maintenance trap.

## Suggested Fix

Add `audio_separator.*` to the existing `ignore_missing_imports` override list in
`engine/pyproject.toml` (alongside `demucs.*`), then delete the `# type: ignore` on the
function-local import in `separate.py`. Remove `demucs.*` from the override at the same
time if no module imports demucs anymore.

## Resolution

Replaced `demucs.*` with `audio_separator.*` in the `[[tool.mypy.overrides]]`
`ignore_missing_imports` list and dropped the now-unused `torchaudio.*` entry. Removed the
`# type: ignore[import-not-found]  # ml-only` on the function-local import in
`separate.py:36`. Verified `cd engine && uv sync --extra ml && uv run mypy` -> green, 71 files.

---

*Filed: 2026-06-30*
*Resolved: 2026-06-30*
