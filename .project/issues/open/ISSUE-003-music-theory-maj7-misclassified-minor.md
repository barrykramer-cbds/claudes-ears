# ISSUE-003: maj7 chords misclassified as minor corrupts Roman-numeral and cadence analysis

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: music_theory.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`parse_chord_quality()` tests for minor before major using a too-loose substring check
that matches the "ma" in "maj":

```python
# music_theory.py:111-118
if 'dim' in quality_part or 'o' in quality_part:
    return 'diminished'
elif 'aug' in quality_part or '+' in quality_part:
    return 'augmented'
elif 'min' in quality_part or 'm' in quality_part[:2]:   # <-- BUG
    return 'minor'
elif 'maj' in quality_part or quality_part == '' or ...:
    return 'major'
```

For a `maj7` chord, `quality_part == "maj7"`, so `quality_part[:2] == "ma"` and
`'m' in 'ma'` is `True` — the function returns `'minor'` and never reaches the `'maj'`
branch on the next line.

This is reachable in-pipeline: `chord_progression.py:14` includes a `'maj7'` template,
so chords are emitted with labels like `"Gmaj7"`, `"Cmaj7"`.

## Reproduction / Evidence

```
parse_chord_quality("Gmaj7") -> 'minor'   (should be 'major')
```

Downstream, `chord_to_roman()` lowercases the numeral for minor qualities
(music_theory.py:216), so a `Vmaj7` becomes `v`. `detect_cadences()` matches authentic /
half / deceptive cadences by `pn == 'V'` (uppercase), so every cadence resolving through
or onto a maj7 dominant/tonic is missed. The `'o'` substring test on line 111 is similarly
broad (matches any label containing the letter o), though no current template triggers it.

## Impact

Silent corruption of the harmonic-analysis output (`_theory.json`): wrong chord qualities,
wrong Roman numerals, and missed cadences for any track using maj7 voicings — common in
jazz, soul, and ballads. `story_reader.py` consumes this file for harmonic meaning, so the
error propagates into the final "story" narrative.

## Suggested Fix

Order major-quality detection before the minor substring test, and tighten the minor test
so it cannot match "maj". Prefer explicit suffix parsing over substring membership:

```python
if quality_part.startswith('dim') or quality_part.startswith('o'):
    return 'diminished'
elif quality_part.startswith('aug') or quality_part.startswith('+'):
    return 'augmented'
elif quality_part.startswith('maj') or quality_part == '' or quality_part[0] in '79':
    return 'major'
elif quality_part.startswith('min') or quality_part.startswith('m'):
    return 'minor'
elif quality_part.startswith('sus'):
    return 'suspended'
else:
    return 'major'
```

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
