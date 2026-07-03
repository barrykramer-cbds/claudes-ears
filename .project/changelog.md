# Claude's Ears — Changelog

> Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Added

- Phase 2 / Window 1: 24-module pipeline package, DuckDB layer, step registry, desktop shell (Gate G2 passed, commit 51e508e).

### Changed

- Restructured `src/` into a self-contained `engine/` uv project, symmetric with `desktop/`.
- Modernized the Python stack: torch 2.12.1, numpy 2.4.6 (`<2.5` numba ceiling), librosa 0.11, scikit-learn 1.9, yt-dlp 2026.6.9.
- Swapped separation runner `demucs` → `audio-separator` (same htdemucs_ft model); lyrics `openai-whisper` → `faster-whisper`.

### Fixed

- ISSUE-015: `audio_separator.*` added to the mypy missing-imports override; dropped stale `demucs.*`/`torchaudio.*` and the `type: ignore` in `separate.py`.

---

## Recent Git History (reconstructed)

### 2026 — Pipeline build-out

- **vocal_narrative** — lead/chorus separation, call-and-response detection
- **chord_progression** — chord detection and progression analysis
- **timbral_decomposition** — NMF component separation
- **music_theory** — Krumhansl-Schmuckler key detection, Roman numerals, cadences
- **story_reader** — lyric-aligned story reading wired into pipeline
- **full_perception** — orchestrates 21 pipeline modules + 3 standalone; `--skip-demucs` and `--batch` modes

---

## Milestones

| Milestone | Status |
|-----------|--------|
| Core pipeline (25 modules) | Complete |
| Orchestration via `full_perception.py` | Complete |
| `version_compare.py` comparison tool | Complete |
| `ai_detector.py` structural AI detection | Complete |
| Tests | Not started |
| Type annotations audit | Not started |
| `ruff` / `mypy` clean pass | Not started |

---

*Last updated: 2026-06-30*
