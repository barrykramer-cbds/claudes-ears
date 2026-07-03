# ISSUE-014: temporal_genome hardcodes track metadata — cannot generalize beyond the author's library

**Severity**: MEDIUM
**Type**: Technical Debt
**Discovered By**: general-purpose (schema mapping)
**Discovered During**: ad-hoc review
**Affected Files**: temporal_genome.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`temporal_genome.py` derives era/year/artist/genre from an in-module **hardcoded `METADATA` dict**
keyed by specific stem-folder names (the author's own library, including baked-in typos like
"Porcelein"/"Evanescense"). Any track not in the dict falls back to `{year: 0, artist: "Unknown",
genre: "unknown", era: "unknown"}`. The cross-era / genre-cluster analysis therefore only works for
the author's exact tracks and silently degrades for everything else.

## Reproduction / Evidence

- `METADATA = { "<exact folder name>": {year, artist, genre, era}, ... }` hardcoded in the module.
- Join is raw string equality on demucs folder names; sentinel `year: 0` marks unknowns.

## Impact

- The temporal/era features (a Phase 5 library differentiator) are non-functional for any library other
  than the author's — a blocker for shipping this as a general personal tool.

## Suggested Fix

Replace the hardcoded dict with real per-track metadata: persist `year/artist/genre/era` as DuckDB
`tracks` columns (sourced from file tags, the `Artist - Title` filename convention, or a lightweight
metadata lookup), and have the temporal/era view query the DB rather than a code constant.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
