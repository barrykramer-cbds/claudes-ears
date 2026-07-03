# ISSUE-013: "Grounded LLM story reading" differentiator is mis-described — story_reader is rule-based

**Severity**: MEDIUM
**Type**: Technical Debt
**Discovered By**: general-purpose (schema mapping)
**Discovered During**: ad-hoc review
**Affected Files**: story_reader.py, semantic_lyrics.py, README.md, .claude/CLAUDE.md, .project/prd.md
**Assigned To**: unassigned
**Status**: Open

---

## Description

The project's headline differentiator — "grounded story reading: acoustic data + lyrics fed into an
LLM for musically-grounded literary analysis (`story_reader.py`)" — does not match the code.
`story_reader.py` is **rule-based** narrative synthesis (`describe_vessel`) and **does not call an LLM**.
The only Claude API call in the codebase lives in `semantic_lyrics.py` (model `claude-sonnet-4-20250514`).

## Reproduction / Evidence

- `story_reader.py`: no `anthropic` / API call; `read_story` composes `vessel` strings from rules.
- `semantic_lyrics.py`: posts to `https://api.anthropic.com/v1/messages` for the semantic reading.
- README.md / CLAUDE.md / prd.md attribute the LLM reading to `story_reader.py`.

## Impact

- The project's stated identity diverges from its implementation — misleading to contributors and users.
- Architecture ambiguity: unclear which module should own the grounded-LLM reading once the pipeline is
  refactored, and how acoustic context should reach the LLM (today the LLM only sees lyrics, not the
  acoustic data the differentiator claims).

## Suggested Fix

Decide the intended design and reconcile:
- **Option A** — make it true: feed `story_reader`'s assembled acoustic context into the LLM call
  (move/extend the `semantic_lyrics` Claude call so it receives vocal-relationship/harmony/emotion context).
- **Option B** — correct the docs to describe the actual split (rule-based vessel in `story_reader`,
  LLM lyric reading in `semantic_lyrics`).
Capture the decision in `prd.md` + `tech-stack.md` and align `PerceptionDocument.story` / `.lyrics`.

## Resolution

[Filled in when resolved.]

---

*Filed: 2026-06-30*
