# ISSUE-011: harmonic_rhythm divides by tempo without guarding a zero value

**Severity**: LOW
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: harmonic_rhythm.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`harmonic_rhythm.py:93-94` reads the tempo from the chords JSON and divides by it. The
`.get` default only covers a missing key, not a present `0`:

```python
tempo = data.get("tempo", 120)
beat_duration = 60.0 / tempo        # ZeroDivisionError if tempo == 0
```

`chord_progression.py:127` writes `"tempo": round(tempo_val, 1)` where `tempo_val` comes
from `librosa.beat.beat_track`. On weakly-pulsed or silent input, `beat_track` can return a
tempo of `0.0`, which is then serialized into `_chords.json`.

## Reproduction / Evidence

A `_chords.json` containing `"tempo": 0` together with at least two chord changes (so the
function reaches line 94) raises:

```
ZeroDivisionError: float division by zero
  at harmonic_rhythm.py:94  beat_duration = 60.0 / tempo
```

The combination is uncommon (a track with chord movement usually yields a non-zero tempo),
which is why it is rated LOW — but the division is genuinely unguarded.

## Impact

Crash on the edge where a track has detectable chord changes but a zero tempo estimate. In
`full_perception.py` the step is `optional=True`, so the run continues; standalone it
aborts.

## Suggested Fix

Validate the tempo before dividing:

```python
tempo = data.get("tempo", 120)
if not tempo or tempo <= 0:
    tempo = 120.0  # fall back to a sane default
beat_duration = 60.0 / tempo
```

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
