# ISSUE-012: semantic_lyrics output is computed then discarded (prints only, never persisted)

**Severity**: MEDIUM
**Type**: Bug
**Discovered By**: general-purpose (schema mapping)
**Discovered During**: ad-hoc review
**Affected Files**: semantic_lyrics.py, full_perception.py
**Assigned To**: unassigned
**Status**: Open

---

## Description

`semantic_lyrics.py` performs VADER sentiment analysis and a Claude API lyric reading, but its
`__main__` only `print(json.dumps(result))` to stdout — there is **no `json.dump` to a file** anywhere
in the module. In pipeline context the orchestrator runs the step but captures nothing, so the entire
lyric-perception result (including the paid LLM call) is **computed and thrown away**.

## Reproduction / Evidence

`semantic_lyrics.py` `__main__`:
```python
result = full_lyric_perception(sys.argv[1], sys.argv[2])
print(json.dumps(result, indent=2))   # never written to disk
```
No sibling `_lyrics.json` (or equivalent) is produced, unlike every other analysis module.

## Impact

- The VADER + LLM lyric analysis never reaches the consolidated output or any consumer.
- Wasted Claude API spend on every run (result is discarded).
- `story_reader` and any consolidator cannot read a lyric-analysis artifact because none exists.

## Suggested Fix

In the in-process refactor, make the module expose `analyze(...) -> dict` and have the
orchestrator/consolidator capture the return value into `PerceptionDocument.lyrics`. Persist a
`<base>_lyrics.json` for parity with the other modules.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
