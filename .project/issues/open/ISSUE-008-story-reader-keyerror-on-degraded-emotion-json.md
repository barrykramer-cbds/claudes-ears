# ISSUE-008: story_reader crashes with KeyError when a context module wrote an error object

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: story_reader.py, emotional_trajectory.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`story_reader.load_context()` assumes every context JSON has the success-path schema and
hard-indexes required keys instead of using `.get()`:

```python
# story_reader.py:199-202
if os.path.exists(emotion_path):
    with open(emotion_path, encoding='utf-8') as f:
        contexts["emotion"] = json.load(f)
    print(f"    Loaded emotional trajectory ({contexts['emotion']['total_phases']} phases)")
```

But `emotional_trajectory.py:61-62` writes an **error object** when its input has no
snapshots:

```python
if not snaps:
    return {"error": "No temporal snapshots found"}
```

That object — `{"error": "..."}` — is dumped to `_emotion.json` (emotional_trajectory.py:199).
`story_reader` then reads it and accesses `['total_phases']`, raising
`KeyError: 'total_phases'`. The same assumption recurs at `find_context_at_time`
(`contexts["emotion"]["phases"]`, story_reader.py:248) and for other layers
(`['total_story_phases']` at :217, `['key']`/`['mode']`/`['total_cadences']` at :238).

## Reproduction / Evidence

1. Run the pipeline on a very short or silent track. `temporal_segmentation` produces no
   snapshots, so `emotional_trajectory` writes `{"error": "No temporal snapshots found"}`
   to `<track>_emotion.json`.
2. `story_reader` loads it and crashes:
   ```
   KeyError: 'total_phases'
     at story_reader.py:202
   ```

The crash is the success-schema assumption colliding with the documented error-schema
its own upstream module emits.

## Impact

`story_reader.py` — the flagship integration layer — aborts on degraded input rather than
degrading gracefully. In `full_perception.py` the step is `optional=True`, so the story is
simply lost; standalone it terminates with an unhandled KeyError.

## Suggested Fix

Treat error objects as "context unavailable" and use `.get()` with defaults throughout
`load_context` / `find_context_at_time`:

```python
data = json.load(f)
if "error" not in data:
    contexts["emotion"] = data
    print(f"    Loaded emotional trajectory ({data.get('total_phases', 0)} phases)")
```

Apply the same `error`-aware, `.get()`-defaulted handling to the relationships, theory,
chords, depth, and stereo layers.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
