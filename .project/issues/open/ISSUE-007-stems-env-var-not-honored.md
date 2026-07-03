# ISSUE-007: Documented CLAUDES_EARS_STEMS env var is ignored by the producer and orchestrator

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: code-review-engineer
**Discovered During**: ad-hoc review
**Affected Files**: run_demucs.py, full_perception.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`CLAUDES_EARS_STEMS` is documented (CLAUDE.md, tech-stack.md, and full_perception.py's own
header) as the demucs stem-output root. Three different components disagree on the source
of truth, and the two that write/discover stems ignore the documented variable entirely:

- Producer — `run_demucs.py:19` reads a **differently named** variable:
  ```python
  out_root = os.environ.get('CLAUDES_EARS_STEMS_ROOT', 'stems')
  ```
- Orchestrator — `full_perception.py:23` hardcodes the path, reading **no** env var:
  ```python
  STEMS_DIR = os.path.join(WORKSPACE, "stems", "htdemucs")
  ```
- Consumers — `story_reader.py:512`, `version_compare.py:51`, `ai_detector.py:309`,
  `genome_map.py:164`, `temporal_genome.py:159` all read `CLAUDES_EARS_STEMS`.

## Reproduction / Evidence

Set the documented variable to a custom location and run the pipeline:

```bash
export CLAUDES_EARS_STEMS=/data/stems/htdemucs
python full_perception.py "song.mp3"
```

- `run_demucs.py` ignores it (reads `CLAUDES_EARS_STEMS_ROOT`) and writes to `./stems/htdemucs/song/`.
- `full_perception.py` ignores it and looks in `./stems/htdemucs/song/` (works by luck in the default case).
- The library-level consumers look in `/data/stems/htdemucs/` and find **nothing** —
  `genome_map.py` / `temporal_genome.py` / `ai_detector.py --batch` report zero tracks.

In the default (unset) case all three happen to resolve to `./stems/htdemucs`, masking the
bug — which is why it survives casual use.

## Impact

Setting the documented configuration variable silently breaks the pipeline: stems are
written to one place and searched for in another. The config contract advertised to users
does not work.

## Suggested Fix

Pick one variable name (`CLAUDES_EARS_STEMS`) and wire it everywhere:

- `run_demucs.py`: derive `out_root` from `CLAUDES_EARS_STEMS` (strip the trailing
  `htdemucs` component, since demucs appends the model name), or read a dedicated
  `CLAUDES_EARS_STEMS_ROOT` that the docs actually mention.
- `full_perception.py:23`: `STEMS_DIR = os.environ.get("CLAUDES_EARS_STEMS", os.path.join(WORKSPACE, "stems", "htdemucs"))`.
- Reconcile the docs in `.project/tech-stack.md` and CLAUDE.md to the chosen names.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
*Resolved: *
