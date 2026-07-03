# Claude's Ears — Build Plan

> **CRITICAL INSTRUCTIONS FOR ALL AGENTS**
>
> ## Project Structure
>
> Project documentation lives in `.project/`:
>
> ```
> .project/
> ├── prd.md            # Product requirements
> ├── tech-stack.md     # Technology choices + target structure
> ├── schema.md         # THE canonical data schema (module outputs → PerceptionDocument → DuckDB)
> ├── build-plan.md     # This file — orchestration manifest + task tracking
> ├── changelog.md      # Version history
> └── issues/           # ISSUE-001..014 (open) — folded into the work, see issue map
> ```
>
> ## What we are building
>
> Refactor the existing **24-module flat Python audio pipeline** into a cross-platform **Electron
> desktop app**. The Python becomes an importable package (`src/claudes_ears/`) with
> `analyze(...) -> dict` functions behind a warm-model **FastAPI sidecar**; module outputs are
> consolidated into a typed **`PerceptionDocument`**, indexed in **DuckDB** (with VSS twin-search),
> and rendered in a **React/Vite/Tailwind/shadcn** UI (Emil-style polish), packaged with
> **PyInstaller + Electron Builder**. Personal **local** tool — NO hosting/queue/auth/server-DB.
> This is a **refactor + reorganize of mostly-working code, not a greenfield rewrite.**
>
> ## Build Discipline (`.claude/rules/build-discipline.md`)
>
> 1. After every task: build → test → lint. Zero warnings, zero errors, zero failures.
> 2. Mark task status in this file the moment it changes.
> 3. **Respect file ownership** — never write outside your assigned boundary during a parallel window.
> 4. **Stop at every gate.** Gates require **human (user) approval**. No agent or Lead auto-proceeds.
> 5. Agents do **not** commit or push — ⚫ Lead owns all git operations.
> 6. Update `.project/changelog.md` at milestones (⚫ Lead only).
>
> ```bash
> # Python build/verify (run from repo root). ruff is scoped to `src tests` — the
> # legacy flat root scripts are pre-refactor and migrate into src/ one-per-agent;
> # ruff's exclude globs can't spare src/ from a root-only rule (basename match),
> # so we scope instead. mypy is scoped via [tool.mypy] files + a path exclude.
> cd engine && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
>
> # Desktop build/verify (pnpm always — never npm/bun)
> cd desktop && pnpm install && pnpm typecheck && pnpm lint && pnpm build
> ```
>
> ## Engineer Assignments
>
> Engineers are defined in `.claude/agents/`. Each agent gets a stable colored dot used in every
> task row. The module fan-out runs **many `python-engineer` instances concurrently** — they share
> the 🟢 dot but each instance owns exactly one module file + its test file (ownership is unique by
> path, not by color). Where marked 🤝 PARALLEL, agents work simultaneously via an agent team with
> **file-boundary isolation** (same working tree, no worktrees).

| Icon | Agent | Domain Boundary |
| ---- | ----- | --------------- |
| 🟢 | `python-engineer` | `src/claudes_ears/**` — analysis modules, pipeline, models, api, cli (one instance per module in fan-out waves) |
| 🟠 | `database-engineer` | `src/claudes_ears/db/**` (`library.py`, `twins.py`); authors `db/schema.sql` in Foundation |
| 🔵 | `react-engineer` | `desktop/**` — Electron shell, React renderer, typed API/SSE client |
| 🎨 | `emil-design-eng` (skill) | UI motion/transition/gesture polish — invoked **by** 🔵 inside `desktop/` |
| 🟣 | `qa-engineer` | `tests/**` integration/E2E suites, golden fixtures, hazard tests |
| 🔴 | `code-review-engineer` | Adversarial review at every gate — no file ownership, read + report |
| ⚙️ | `devops-engineer` | Packaging — PyInstaller spec, Electron Builder, signing/notarization, weight bundling |
| ⚫ | Lead | Foundation contract, gates, all git ops, `.project/` curation, conflict resolution |

---

## Orchestration Config

| Phase | Strategy | Isolation | Agents | Cloud | Gate After |
| ----- | -------- | --------- | ------ | ----- | ---------- |
| **1. Foundation** | Sequential | — | ⚫ Lead, 🟢 python-eng, 🟠 db-eng | No | **Yes — G1** |
| **2. Parallel Window 1** | 🤝 Parallel (team) | File boundaries | 🟢 ×12 (module wave 1), 🟠 db, 🟢 consolidator/orchestrator, 🔵 react (+🎨) | Partial ☁️ | **Yes — G2** |
| **3. Parallel Window 2** | 🤝 Parallel (team) | File boundaries | 🟢 ×12 (module wave 2), 🟢 api, 🔵 react (+🎨), 🟠 db | Partial ☁️ | **Yes — G3** |
| **4. Integration** | Sequential | — | 🟢 python-eng, 🔵 react-eng (⚫ Lead-coordinated) | No | **Yes — G4** |
| **5. Hardening** | 🤝 Parallel (team) | File boundaries | 🟣 qa, 🔴 code-review, ⚙️ devops (prep) | Yes ☁️ | **Yes — G5** |
| **6. Packaging & Release** | Sequential | — | ⚙️ devops-eng (⚫ Lead-coordinated) | Partial ☁️ | **Yes — G6 (final)** |

**Why this shape.** Foundation is the shared contract (`models/`, `steps.py`, `db/schema.sql`) —
sequential and frozen first. Once frozen, four tracks fan out concurrently: **(A)** the
embarrassingly-parallel module refactor (the headline fan-out — each of 24 modules is a one-file
unit of work), **(B)** the DuckDB layer (binds only to the 12-dim genome spec), **(C)** the
consolidator/orchestrator/API (binds to `models/` + `steps.py`), and **(D)** the desktop app (binds
only to the typed `PerceptionDocument` shape, mirrored as Zod). Integration wires the real
end-to-end; hardening and packaging are the dependent tail.

---

## Conflict Zones

> Files more than one agent could touch. **NEVER modified during a parallel window.** All changes
> happen in a sequential phase or at a gate. Each has a resolution strategy.

| File / Path | Touched By | Resolution Strategy |
| ----------- | ---------- | ------------------- |
| `pyproject.toml` / `uv.lock` | every Python track (deps) | **All** runtime + dev deps declared in Foundation 1.1 (ML tree + fastapi, uvicorn, sse-starlette, duckdb, httpx, pytest, pytest-asyncio). Frozen during windows. A missing dep is **reported to ⚫ Lead**, who adds it and regenerates `uv.lock` **at the gate only**. |
| `src/claudes_ears/models/perception.py` + `models/jobs.py` | Foundation authors; **all tracks read** | **Frozen at G1.** The `PerceptionDocument` is the canonical contract (every domain `\| None` — the ISSUE-008 fix). Any change is ⚫ Lead-only and forces a re-gate. |
| `src/claudes_ears/pipeline/steps.py` | Foundation authors; **all read** | **Frozen at G1.** Step registry: name, `analyze` signature, deps, optional flag. New steps → ⚫ Lead at a gate. |
| `src/claudes_ears/db/schema.sql` | 🟠 db-eng authors in Foundation; read after | **Frozen at G1.** DDL changes only in a sequential phase (schema-in-foundation discipline). |
| `src/claudes_ears/config.py` (env: `CLAUDES_EARS_STEMS`/`_MUSIC`) | Foundation authors; modules read | **Frozen at G1.** Single source of truth for env vars (the ISSUE-007 fix). |
| `src/claudes_ears/_sanitize.py` (non-finite float → `None`) | Foundation authors; modules + consolidator read | **Frozen at G1.** Boundary sanitizer for the NaN→invalid-JSON hazards. |
| `src/claudes_ears/cli.py` | Foundation authors (registry-driven dispatcher) | Auto-discovers steps from `steps.py` — **no per-module edits**, so it is never touched during the fan-out. |
| `desktop/package.json` + `pnpm-lock.yaml` | 🔵 react (build), ⚙️ devops (packaging) | 🔵 owns during Windows 1–2; ⚙️ edits only in Phase 6 (sequential). Collect dep adds, ⚫ Lead applies at gate; lockfile regenerated at gates only. |
| `desktop/` config (`vite.config.ts`, `electron-builder.yml`, `tailwind.config`, `tsconfig`) | 🔵 react (Window 1), ⚙️ devops (Phase 6) | Set once in Window 1 Track D, frozen during Window 2; ⚙️ touches `electron-builder.yml` only in Phase 6. |
| repo-root legacy `*.py` (e.g. `vocal_narrative.py`) | the module's mover deletes its **own** root file | Each root script is owned by exactly one fan-out agent (the one porting it). `full_perception.py` + `run_demucs.py` removal is ⚫ Lead, Phase 4 (after all modules moved). |
| `.project/**` (incl. `issues/`, `changelog.md`, this file) | ⚫ Lead only | Agents may **file** issues into `issues/open/`; ⚫ Lead curates, updates build-plan/changelog, closes issues. |

---

## Build Verification Protocol

| Context | What to Run | Who Runs It |
| ------- | ----------- | ----------- |
| During a window — Python agent (per owned paths) | `uv run ruff check <paths> && uv run ruff format --check <paths> && uv run mypy <paths> && uv run pytest tests/<owned>` | each 🟢 / 🟠 agent for its boundary |
| During a window — desktop agent | `cd desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build` | 🔵 react-eng |
| At gates — full Python | `cd engine && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` | ⚫ Lead |
| At gates — full desktop | `cd desktop && pnpm install && pnpm typecheck && pnpm lint && pnpm build` | ⚫ Lead |
| Before release | full Python + desktop + **packaged-installer smoke test on macOS and Windows** | ⚫ Lead / ⚙️ devops |

**Rule:** during parallel windows each agent verifies **only its own boundary**. The full-project
suite is a ⚫ Lead responsibility, run at the gate. Zero warnings / zero errors before any transition.

---

## Status Legend

| Icon | Status | Description |
| ---- | ------ | ----------- |
| ⬜ | Not Started | Task has not begun |
| 🔄 | In Progress | Currently being worked on |
| ✅ | Completed | Task finished |
| ⛔ | Blocked | Cannot proceed — external dependency |
| ⚠️ | Has Blockers | Waiting on another task |
| 🔍 | In Review | Pending review/approval |
| 🚫 | Skipped | Intentionally not doing |
| ⏸️ | Deferred | Postponed to later phase |
| ☁️ | Cloud Eligible | Can be offloaded to a cloud VM |
| 🤝 | Agent Team | Parallel phase, file-boundary isolation |

---

## Project Progress Summary

```
Phase 1: Foundation            [████████████████████] 100%  ✅ (G1 approved)
Phase 2: Parallel Window 1     [████████████████████] 100%  ✅ G2 passed (51e508e)
Phase 3: Parallel Window 2     [████████████████████] 100%  ✅ committed a1ab948 (G3 review deferred by user)
  ↳ Frontend Polish (interlude)  [██████░░░░░░░░░░░░░░░]      🔄 crypto/dropzone fixes landed + verified (uncommitted)
Phase 4: Integration           [░░░░░░░░░░░░░░░░░░░░]   0%  ⬜ prod wiring + library CRUD; scope widened by 2026-06-30 audit
Phase 5: Hardening             [░░░░░░░░░░░░░░░░░░░░]   0%  ⬜
Phase 6: Packaging & Release   [░░░░░░░░░░░░░░░░░░░░]   0%  ⬜
────────────────────────────────────────────────────────────
Overall Progress               [█████████████░░░░░░░]  66%
```

| Phase | Tasks | Completed | Blocked | Deferred | Progress | Agents |
| ----- | ----- | --------- | ------- | -------- | -------- | ------ |
| 1. Foundation | 15 | 15 | 0 | 0 | 100% | ⚫ 🟢 🟠 |
| 2. Window 1 | 30 | 30 | 0 | 0 | 100% | 🟢×12 🟠 🔵 🎨 |
| 3. Window 2 | 31 | 31 | 0 | 0 | 100% | 🟢×12 🟠 🔵 🎨 |
| 4. Integration | 18 | 0 | 0 | 0 | 0% | 🟢 🔵 ⚫ |
| 5. Hardening | 12 | 0 | 0 | 0 | 0% | 🟣 🔴 ⚙️ |
| 6. Packaging | 10 | 0 | 0 | 0 | 0% | ⚙️ ⚫ |
| **Total** | **116** | **76** | **0** | **0** | **66%** | |

---

## Audit Snapshot — 2026-06-30

Full-stack capability audit (4 parallel readers) before starting Phase 4. Headline: **the backend is
real, the frontend is dormant behind the mock flag.** Confirms the plan and widens its scope.

- **Real & green (unit-tested, never run on real audio):** in-process orchestrator (21 steps, no
  subprocess), real SSE progress, live DuckDB persistence (`tracks` + 12-dim `genome_vectors`, upsert on
  every completed job), HNSW/VSS sonic-twin search. Backend endpoints: `POST /jobs`, `GET /jobs/{id}`,
  `/jobs/{id}/perception`, `/jobs/{id}/events` (SSE), `GET /library`, `/library/{id}/twins`.
- **Dormant:** `desktop/lib/api.ts` has a fully-wired real HTTP/SSE client gated by `VITE_USE_MOCK`
  (defaults **true**). The "song" everywhere in dev is the `mock/perception.ts` fixture ("The Weight").
- **Frontend library is in-memory only** — seeded on job completion, wiped on reload; never calls
  `GET /library`. Backend persistence exists but is unconsumed.
- **Gaps not previously in the plan → added below:** no rename/delete/per-track-GET; jobs are in-memory
  (restart orphans them), no job list/cancel; no upload endpoint (`audio_path` must be sidecar-local);
  `library.duckdb` is CWD-relative (fragile when packaged); `get_track_metadata → temporal_genome.analyze`
  is defined but never invoked at runtime.
- **Runtime check:** `ffmpeg`, `audio_separator`, `faster_whisper`, orchestrator all import. **CPU-only,
  no GPU** — separation will take minutes/track. Dead root `full_perception.py` confirmed (subprocesses
  scripts that no longer exist) — 4.1.5 deletes it.
- **4.1.1 (real run) blocked:** no real audio in the repo. Need a vocal track placed in `./music/` or a
  path provided to flush out raw-shape mismatches.

---

## Issue Integration Map

> Where each open issue dies. **Most expire naturally during their module's refactor.** Structural
> ones (001, 008, 012) die with the architecture change; 013/014 are scheduled architecture decisions.

| Issue | Sev | Dies In | Mechanism |
| ----- | --- | ------- | --------- |
| **001** shell injection (`full_perception.py`) | HIGH | P1 (orchestrator design) → P4 (root removal) | In-process imports replace subprocess `os.system` f-strings entirely; `full_perception.py` deleted in P4 |
| **002** vocal_narrative precedence crash | HIGH | P2 — `2.1.4` vocal_narrative refactor | Fix index-precedence bug while extracting `analyze()` |
| **003** music_theory maj7 → minor | MED | P3 — `3.1.4` music_theory refactor | Fix `parse_chord_quality()` substring order |
| **004** stereo_field NaN corrcoef | MED | P3 — `3.1.1` stereo_field + consolidator sanitizer | Guard zero-variance channel; `_sanitize.py` nulls non-finite |
| **005** temporal_segmentation NaN (short audio) | MED | P3 — `3.1.2` temporal_segmentation + `3.1.5` emotional_trajectory | Guard `len(snaps)//3 == 0`; mean-of-empty → `None` |
| **006** timbral NMF n_components crash | MED | P2 — `2.1.11` timbral_decomposition refactor | Bound `n_components`; `analyze()` no longer reads `sys.argv` |
| **007** stems env var not honored | MED | P1 (`config.py`) → P2 separation → P4 verify | Single `config.py` source of truth; separation + orchestrator read it |
| **008** story_reader KeyError (degraded JSON) | MED | **P1 typed contract** + P3 — `3.1.7` story_reader | Every domain `\| None`; derived `analyze()` takes upstream dict via `.get`; consolidator validates once |
| **009** semantic_lyrics unencoded URL | LOW | P3 — `3.1.6` semantic_lyrics refactor | `urllib.parse.quote` the artist/title path |
| **010** vocal_intervals octave modulo | LOW | P2 — `2.1.3` vocal_intervals refactor | Fix always-true guard after `% 12` |
| **011** harmonic_rhythm tempo zero-division | LOW | P3 — `3.1.4`/`3.1.8` harmonic_rhythm refactor | Guard present-but-zero tempo (not just missing key) |
| **012** semantic_lyrics output discarded | MED | P2 consolidator + P3 — `3.1.6` | `analyze()` **returns** the dict; consolidator captures it (in-process) |
| **013** LLM story reading misattributed | MED | **P1 decision** `1.4.1` + P4 doc reconcile | Decide: `semantic_lyrics` owns the Claude API; `story_reader` stays rule-based; shape `lyrics` vs `story` sub-models accordingly; update README/CLAUDE.md/prd in P4 |
| **014** temporal_genome hardcoded METADATA | MED | **P1 decision** `1.4.2` + P3 — `3.1.11` + P4 wire | `analyze()` takes a `metadata` param; metadata becomes DuckDB columns; wired to real per-track metadata in P4 |

Schema findings #4 (genome vector never persisted) and #5 (`ai_detector --batch` array-vs-object) are
build notes handled in the consolidator (`2.3.2`) and `ai_detector` refactor (`3.1.8`).

---

## Phase 1: Foundation

> **Sequential. ⚫ Lead owns everything.** This is the shared contract every downstream track binds
> to. It MUST complete and pass **G1** before any parallel work begins. These are the most important
> tasks in the plan — a bad contract poisons all four downstream tracks.
>
> **File Ownership:** Lead session owns the whole tree. 🟢 python-eng and 🟠 db-eng act as
> sequential sub-agents within the Lead session (no concurrency, no boundary risk).

### 1.1 Package & tooling scaffold

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ✅ | 1.1.1 | **`pyproject.toml` + uv** — author `pyproject.toml` targeting Python 3.12 with **all** runtime deps (librosa, soundfile, numpy, scipy, demucs, scikit-learn, torch, torchaudio, openai-whisper, vaderSentiment, httpx, yt-dlp, ffmpeg-python, **fastapi, uvicorn, sse-starlette, duckdb, pydantic≥2**) and dev deps (**ruff, mypy, pytest, pytest-asyncio**). Generate `uv.lock`. Keep `requirements.txt` working (additive migration). | 🟢 python-eng |
| ✅ | 1.1.2 | **ruff + mypy + pytest config** — in `pyproject.toml`: ruff (lint+format, zero-warning), mypy **strict**, pytest with `tests/` rootdir. Reconcile/replace the stray root `ruff.toml`. | 🟢 python-eng |
| ✅ | 1.1.3 | **Package skeleton** — create `src/claudes_ears/` with `analysis/ separation/ pipeline/ models/ db/ api/ api/routes/` and minimal `__init__.py` everywhere (no business logic). Create `tests/` mirroring `src/`. | 🟢 python-eng |
| ✅ | 1.1.4 | **`config.py`** — `src/claudes_ears/config.py`: single source of truth for `CLAUDES_EARS_STEMS` (default `./stems/htdemucs`) and `CLAUDES_EARS_MUSIC` (default `./music`) via `pathlib.Path`. **(ISSUE-007 root fix.)** | 🟢 python-eng |
| ✅ | 1.1.5 | **`_sanitize.py`** — `src/claudes_ears/_sanitize.py`: recursive non-finite-float→`None` and int/float coercion helper used at every output boundary. Covers the NaN→invalid-JSON + int-vs-float "0" hazards (schema §5). | 🟢 python-eng |

### 1.2 The typed contract (the keystone)

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ✅ | 1.2.1 | **`models/perception.py`** — Pydantic v2 `PerceptionDocument` + every sub-model exactly per `schema.md` §2 (`TrackMeta`, `SeparationInfo`, `StemAnalysis`, `VocalAnalysis{layers,intervals,narrative,relationships,register,breath}`, `RhythmAnalysis`, `HarmonyAnalysis{chords,harmonic_rhythm,theory}`, `TimbreAnalysis`, `SpatialAnalysis`, `StructureAnalysis`, `EmotionTrajectory`, `LyricsAnalysis`, `StoryReading`, `AiDetection`, `GenomeVector`). **Every domain `\| None`** (the ISSUE-008 fix). Model the variant/union array shapes from schema §5 (silence frames drop keys → `None`). Add `schema_version`. | 🟢 python-eng |
| ✅ | 1.2.2 | **`GenomeVector` (12-dim)** — in `models/perception.py`, model the fixed 12-float vector with the named dims from `schema.md` §3 (vocal_pitch…texture_harmonic). This is the DuckDB VSS contract. | 🟢 python-eng |
| ✅ | 1.2.3 | **`models/jobs.py`** — `Job`, `JobStatus` (enum), `ProgressEvent` (the SSE payload: step name, index/total=21, status, optional message). In-memory job model — no persistence fields. | 🟢 python-eng |

### 1.3 Step registry, conventions & analysis stubs

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ✅ | 1.3.1 | **`pipeline/steps.py`** — the frozen step registry: ordered list of `Step(name, dotted_path, analyze_signature, depends_on, optional)` covering all 24 modules in phase order (separation → stem → vocal → full-mix → derived → library). Document the **`analyze()` signature convention**: audio-consumers take `Path`; derived modules take upstream **dict(s)** (no sibling-JSON reads — kills the filename-replace hazard, schema §5); library/pair modules take lists/`PerceptionDocument`s + `metadata`. | 🟢 python-eng |
| ✅ | 1.3.2 | **Analysis stubs (×24 + separation)** — for every module create `src/claudes_ears/analysis/<module>.py` (and `separation/separate.py`) as a typed stub: `def analyze(...) -> dict: raise NotImplementedError`, signature matching `steps.py`. This makes `steps.py`, the orchestrator, and the consolidator **type-check and import cleanly at G1**; fan-out agents replace each stub body. | 🟢 python-eng |
| ✅ | 1.3.3 | **`cli.py`** — registry-driven dispatcher (`python -m claudes_ears <step> <path>`): iterates `steps.py`, no per-module subcommand edits. Replaces the per-file CLI shims. | 🟢 python-eng |

### 1.4 Architecture decisions & DB schema

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ✅ | 1.4.1 | **DECISION — LLM ownership (ISSUE-013)** — record in Notes & Decisions: `semantic_lyrics` owns the Claude API call (the grounded LLM reading); `story_reader` stays **rule-based** synthesis. Shape `models.lyrics` (LyricsAnalysis, holds VADER + LLM result) vs `models.story` (StoryReading, rule-based) accordingly. Doc reconciliation (README/CLAUDE.md/prd) scheduled in P4. When touching the model id, consult the `claude-api` reference. | ⚫ Lead |
| ✅ | 1.4.2 | **DECISION — track metadata (ISSUE-014)** — record: era/year/artist/genre become **real per-track metadata → DuckDB columns**, not a hardcoded dict. `temporal_genome.analyze()` takes a `metadata` param. Define the metadata columns now so 🟠 db-eng and the consolidator agree. | ⚫ Lead |
| ✅ | 1.4.3 | **`db/schema.sql`** — author the canonical DDL per `schema.md` §3: `tracks` (incl. the new metadata columns from 1.4.2), `genome_vectors(track_id, vector FLOAT[12])`, and the HNSW/VSS index. Idempotent upsert by `track_id`. **Frozen after G1.** | 🟠 db-eng |
| ✅ | 1.4.4 | **BUILD CHECK** — `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest` passes clean (stubs + models + registry type-check; empty test run is green). | ⚫ Lead |

---

## Gate G1: Foundation Frozen

### Prerequisites
- [ ] 1.1–1.4 complete; full Python suite green
- [ ] `models/perception.py`, `models/jobs.py`, `pipeline/steps.py`, `config.py`, `_sanitize.py`, `db/schema.sql` reviewed

### Gate Protocol
1. ⚫ Lead summarizes the frozen contract (models, registry, signatures, DDL) to the user.
2. 🔴 code-review-engineer reviews the contract for type-safety + optionality correctness (the ISSUE-008 fix) and the 12-dim genome spec.
3. **USER REVIEWS AND APPROVES — no auto-proceed.** This is the most important gate: everything binds to what is frozen here.
4. ⚫ Lead commits + pushes the foundation.
5. ⚫ Lead spins up the Window 1 agent team with the file-ownership map below.

### Conflict Resolution Priority
1. `models/perception.py` — canonical source of truth for every downstream shape.
2. `pyproject.toml` / `uv.lock` — regenerate from the full declared dep set.
3. `steps.py` / `db/schema.sql` — must agree on names and the genome dimension.

---

## Phase 2: Parallel Window 1 🤝

> **PARALLEL — agent team, file-boundary isolation.** Depends on: G1 (frozen contract).
> The headline fan-out begins here. Four tracks run concurrently; concurrency budget ~16 agents
> (12 module instances + db + consolidator + desktop). Each agent verifies only its own boundary.

### File Ownership (This Window)

| Agent | Owns (read/write) | Reads only (no write) |
| ----- | ----------------- | --------------------- |
| 🟢 python-eng ×12 (one per module) | `src/claudes_ears/analysis/<their module>.py` + `tests/analysis/test_<module>.py` + delete their own repo-root `<module>.py` | `models/`, `steps.py`, `config.py`, `_sanitize.py`, `schema.md` |
| 🟢 python-eng (Track C) | `src/claudes_ears/pipeline/consolidator.py`, `pipeline/orchestrator.py` + `tests/pipeline/` | `models/`, `steps.py`, all `analysis/` stubs, `schema.md` |
| 🟠 db-eng (Track B) | `src/claudes_ears/db/library.py`, `db/twins.py` + `tests/db/` | `db/schema.sql` (frozen), `models/perception.py` (`GenomeVector`) |
| 🔵 react-eng + 🎨 (Track D) | `desktop/**` (scaffold, electron main/preload, shell, `lib/api.ts`, tokens, drop-zone, progress UI) | `models/perception.py` → mirrored as Zod/TS types |

**Frozen (no writes by anyone):** `pyproject.toml`, `models/`, `steps.py`, `config.py`,
`_sanitize.py`, `db/schema.sql`, `cli.py`, `.project/`.

### 2.1 Module Refactor — Wave 1 (12 independent units)

> Each row is **one agent, one commit-sized unit, one pass**: move `<module>.py` root→`analysis/`,
> extract a typed `analyze(...) -> dict` from the `__main__`/CLI body (import-pure: no `sys.argv`,
> no top-level side effects), fix the mapped issue, full type hints (mypy strict), sanitize outputs
> via `_sanitize.py`, write `tests/analysis/test_<module>.py` (happy + issue edge case + degraded/empty
> input), delete the root file. Verify own boundary. **No cross-module imports.**

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 2.1.1 | **separation** — port `run_demucs.py` → `separation/separate.py`; `analyze()`/`separate()` reads stem root from `config.py` (**ISSUE-007**), warm-model friendly (no per-call reimport). | 🟢 python-eng |
| ⬜ | 2.1.2 | **analyze_stems** — port → `analysis/analyze_stems.py`; emits the per-stem dict that feeds the 12-dim genome vector (schema §3). Coerce int/float "0" fallbacks. | 🟢 python-eng |
| ⬜ | 2.1.3 | **vocal_intervals** — port + fix **ISSUE-010** (always-true guard after `% 12`). | 🟢 python-eng |
| ⬜ | 2.1.4 | **vocal_narrative** — port + fix **ISSUE-002** (index-precedence crash on all-zero piptrack frame). | 🟢 python-eng |
| ⬜ | 2.1.5 | **vocal_relationships** — port; preserve the `solo\|support\|dialogue\|opposition\|merge\|withdraw\|silence` label union; silence frames drop keys → `None`. | 🟢 python-eng |
| ⬜ | 2.1.6 | **vocal_layers** — port; model the optional echo/dense-region arrays. | 🟢 python-eng |
| ⬜ | 2.1.7 | **register_tracking** — port; keep unrounded f0 fields; model variant `moments[*]`. | 🟢 python-eng |
| ⬜ | 2.1.8 | **breath_detection** — port; handle empty-vs-full root shape (schema §5). | 🟢 python-eng |
| ⬜ | 2.1.9 | **groove_timing** — port; branch the 3 root shapes (incl. `error`); never index blindly. | 🟢 python-eng |
| ⬜ | 2.1.10 | **freq_interaction** — port; `territory == {}` when `<2` stems. | 🟢 python-eng |
| ⬜ | 2.1.11 | **timbral_decomposition** — port + fix **ISSUE-006** (bound `n_components` to spectrogram size; remove `sys.argv` read). | 🟢 python-eng |
| ⬜ | 2.1.12 | **chord_progression** — port; emits the `segments[]`/`tempo` consumed (in-process) by music_theory + harmonic_rhythm. | 🟢 python-eng |
| ⬜ | 2.1.13 | ☁️ **BUILD CHECK (Wave 1)** — ⚫ Lead runs full Python suite over all 12 moved modules: `uv run ruff check . && mypy . && pytest tests/analysis`. Cloud-offloadable (deterministic success criteria). | ⚫ Lead |

### 2.2 Track B — DuckDB layer (concurrent)

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 2.2.1 | **`db/library.py`** — open/init the embedded DuckDB file, apply `schema.sql`, idempotent **upsert by `track_id`** of `tracks` rows from a `PerceptionDocument` (key/mode/tempo/valence/arousal/ai_*/metadata). No ETL — reads the doc in place. | 🟠 db-eng |
| ⬜ | 2.2.2 | **`db/twins.py`** — load the VSS extension, build/refresh the HNSW index on `genome_vectors.vector` (`FLOAT[12]`), nearest-neighbour twin query returning ranked `track_id`s + distances. | 🟠 db-eng |
| ⬜ | 2.2.3 | **DB tests** — `tests/db/`: upsert idempotency (no dup rows on re-analysis), 12-dim insert, twin-search ordering on a small synthetic set. | 🟠 db-eng |
| ⬜ | 2.2.4 | ☁️ **BUILD CHECK** — `uv run mypy src/claudes_ears/db && uv run pytest tests/db` clean. | 🟠 db-eng |

### 2.3 Track C — Consolidator + Orchestrator skeleton (concurrent)

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 2.3.1 | **`pipeline/consolidator.py`** — per-domain mappers raw module dict → typed sub-model, binding to `schema.md` §2 shapes. Branch on every discriminator (mono/stereo, emotion `{error}`/full, groove 3-shapes, harmonic_rhythm `windows` vs `harmonic_rhythm_windows`); degraded/missing step → that domain `= None`; `_sanitize` at the boundary. **Validates once → PerceptionDocument** (ISSUE-008 + 012 capture point). | 🟢 python-eng |
| ⬜ | 2.3.2 | **Genome-vector extraction** — in the consolidator, compute the 12-dim `GenomeVector` from the `analyze_stems` dict per `schema.md` §3 (the vector that `genome_map` computes but never persists — schema finding #4). Persisted into `PerceptionDocument.genome`. | 🟢 python-eng |
| ⬜ | 2.3.3 | **`pipeline/orchestrator.py`** — replaces `full_perception.py`: drives `steps.py` in phase order via **in-process `analyze()` calls** (warm models, no subprocess — the **ISSUE-001** root fix), passing upstream dicts to derived steps, emitting `ProgressEvent`s. Imports modules lazily via the registry (stubs still valid). Supports single-track + `--skip-demucs`. | 🟢 python-eng |
| ⬜ | 2.3.4 | **Pipeline tests** — `tests/pipeline/`: consolidator nulls a degraded domain instead of raising; genome vector has 12 finite floats; orchestrator visits steps in dependency order (against stubs). | 🟢 python-eng |
| ⬜ | 2.3.5 | **BUILD CHECK** — `uv run mypy src/claudes_ears/pipeline && uv run pytest tests/pipeline` clean. | 🟢 python-eng |

### 2.4 Track D — Desktop shell + report skeleton (concurrent, bound to mock data)

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 2.4.1 | **Scaffold `desktop/`** — Vite + React 19 + TS + Tailwind (`@theme` design tokens) + shadcn/ui; `electron/main.ts` + `preload.ts` skeleton (will spawn the sidecar later); `package.json` (pnpm). Per `react.md` / `css-tailwind-react.md`. | 🔵 react-eng |
| ⬜ | 2.4.2 | **`lib/api.ts` typed client + Zod** — mirror `PerceptionDocument` + `ProgressEvent` as Zod schemas (single source: schema.md / `models/`); typed fetch client + **SSE** consumer. Zod-validate at the boundary (`react.md`). | 🔵 react-eng |
| ⬜ | 2.4.3 | **App shell + drag-drop** — TanStack Router shell; native-file **drop zone** ("drop a song in and watch it get heard"); Zustand store for job/progress state (server data via TanStack Query). Bound to a **mock** `PerceptionDocument` + mock SSE. | 🔵 react-eng |
| ⬜ | 2.4.4 | 🎨 **Progress UI (21 stages)** — live per-step progress with Emil-doctrine motion (purpose, ease-out, sub-300ms, `prefers-reduced-motion`). Invoke `emil-design-eng`. | 🔵 react-eng + 🎨 |
| ⬜ | 2.4.5 | **Desktop tests + BUILD CHECK** — `cd desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build` clean; Zod round-trips the mock doc. | 🔵 react-eng |

---

## Gate G2: Window 1 Merge ✅ PASSED (2026-06-30, commit 51e508e)

### Prerequisites
- [x] All 🟢 Wave-1 module agents signaled completion (12 modules moved, issues fixed, tests pass)
- [x] 🟠 db layer, 🟢 consolidator/orchestrator, 🔵 desktop shell signaled completion

### Gate Protocol
1. ⚫ Lead summarizes per-agent changes to the user (modules moved, issues closed: 002, 006, 007, 010, plus 001/012 mechanism in place).
2. 🔴 code-review-engineer reviews the merged window — type safety, optionality, no cross-module imports, no boundary violations.
3. **USER REVIEWS AND APPROVES — no auto-proceed.**
4. ⚫ Lead runs full Python suite + full desktop build; fixes any cross-file fallout; adds any reported deps to `pyproject.toml` and regenerates `uv.lock`.
5. ⚫ Lead commits + pushes; ⚫ Lead moves closed issues to `issues/closed/`; updates changelog.
6. ⚫ Lead re-spins the team for Window 2.

### Conflict Resolution Priority
1. `models/` — unchanged; if any agent needed a model tweak, it is a Lead decision + potential re-gate.
2. `pyproject.toml`/`uv.lock` — merge reported deps, regenerate.
3. Test fixtures — canonical golden `PerceptionDocument` belongs to 🟣 qa later; dedupe ad-hoc fixtures.

---

## Phase 3: Parallel Window 2 🤝

> **PARALLEL — agent team.** Depends on: G2 (Window 1 committed: consolidator, db layer, desktop
> shell all exist and are gated). Window 2 builds **on** Window 1: the API imports the consolidator
> + db; renderer views fill in the shell; module Wave 2 completes the fan-out.

> **Status (2026-06-30) — uncommitted, sitting at G3.** Done & verified green (engine: ruff/mypy(91)/pytest
> 282, zero-warnings enforced via `filterwarnings=error`; desktop: typecheck/lint/test 13/build):
> 12 Wave-2 module ports (issues 003/004/005/009/011/014 fixed), FastAPI sidecar (`api/`), db metadata
> + twins, and all 7 renderer tabs against the mock `PerceptionDocument`.
> **Design pivot:** a full **design system** now lives in `.project/design/` (`design-system.md`,
> `tokens.css`, `palette.html`, `app-shell.html` + previews) — Linear-derived cold-dark, no cyan,
> 6-voice taxonomy palette. The renderer was built tab-first; it still needs the **persistent
> Library-sidebar app shell** (3.4.6) so launch reads as a workspace, not a bare drop card.
> **Mock is dev-only** — production wiring (Electron spawns the sidecar, drop mock) is Phase 4.2.
> Stop hook rewritten subtree-aware (engine via `.venv/bin`, desktop via pnpm; Stop-only). ISSUE-015 closed.

### File Ownership (This Window)

| Agent | Owns (read/write) | Reads only |
| ----- | ----------------- | ---------- |
| 🟢 python-eng ×12 (one per module) | `analysis/<their module>.py` + `tests/analysis/test_<module>.py` + delete own root file | `models/`, `steps.py`, `_sanitize.py`, `schema.md`, the Window-1 modules they take dicts from |
| 🟢 python-eng (Track C) | `src/claudes_ears/api/**` (`app.py`, `routes/jobs.py`, `routes/library.py`, `sse.py`) + `tests/api/` | `pipeline/` (consolidator+orchestrator), `db/`, `models/` |
| 🟠 db-eng | `db/library.py` (metadata columns wiring for ISSUE-014), `db/twins.py` finalize | `db/schema.sql` |
| 🔵 react-eng + 🎨 | `desktop/renderer/src/**` (report views, library/twins view) | `lib/api.ts` types |

**Frozen:** same as Window 1 (`models/`, `steps.py`, `db/schema.sql`, configs, `pyproject.toml`).

### 3.1 Module Refactor — Wave 2 (12 units; derived take upstream dicts)

> ✅ **Done (2026-06-30) — all 12 ported, issues fixed, verified green; uncommitted at G3.**

> Same one-agent-one-unit pass as Wave 1. Derived modules take their upstream **dict** as a param
> (no sibling-JSON disk reads) — the orchestrator supplies it. Library/pair modules take lists /
> `metadata` / `PerceptionDocument`s.

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 3.1.1 | **stereo_field** — port + fix **ISSUE-004** (guard zero-variance channel before corrcoef → `None` not NaN); branch mono vs stereo root. | 🟢 python-eng |
| ⬜ | 3.1.2 | **temporal_segmentation** — port + fix **ISSUE-005** (guard `len(snaps)//3 == 0`; mean-of-empty → `None`); `narrative` may be `{}`. | 🟢 python-eng |
| ⬜ | 3.1.3 | **depth_reverb** — port; coerce int/float fallbacks; optional `rt60_std`. | 🟢 python-eng |
| ⬜ | 3.1.4 | **music_theory** — port; `analyze(chords: dict)`; fix **ISSUE-003** (test major before minor); **sort** `unique_numerals` (deterministic, schema §5); preserve nullable `analyzed_chords[].analysis`; sanitize `key_confidence` NaN. | 🟢 python-eng |
| ⬜ | 3.1.5 | **harmonic_rhythm** — port; `analyze(chords: dict)`; fix **ISSUE-011** (guard present-but-zero tempo); normalize `windows` vs `harmonic_rhythm_windows` to one field name. | 🟢 python-eng |
| ⬜ | 3.1.6 | **emotional_trajectory** — port; `analyze(temporal: dict)`; fix **ISSUE-005** mean-of-empty branch; emit full shape or `None` (not `{error}`). | 🟢 python-eng |
| ⬜ | 3.1.7 | **semantic_lyrics** — port; fix **ISSUE-009** (`urllib.parse.quote` the lyrics URL); fix **ISSUE-012** (`analyze()` **returns** the VADER+LLM dict, no print-only). Owns the Claude API call per decision 1.4.1 — consult the `claude-api` reference for the current model id. | 🟢 python-eng |
| ⬜ | 3.1.8 | **story_reader** — port; `analyze(context: dict)` reads upstream via `.get` (no hard-indexing — **ISSUE-008** at the module level); stays **rule-based** (decision 1.4.1). | 🟢 python-eng |
| ⬜ | 3.1.9 | **ai_detector** — port; `analyze(stem_dir, vocal_outputs)`; normalize single-mode object vs `--batch` array to **one** return type (schema finding #5). | 🟢 python-eng |
| ⬜ | 3.1.10 | **genome_map** — port (library-level); `analyze(stem_analyses: list[dict])` → cross-track stats. In the app these stats are **derived from DuckDB**, so the module stays a tool, not a pipeline writer. | 🟢 python-eng |
| ⬜ | 3.1.11 | **temporal_genome** — port + fix **ISSUE-014**: `analyze(genome_map, metadata)` — **no hardcoded METADATA dict**; era/year/artist/genre come from the passed metadata (DB columns). | 🟢 python-eng |
| ⬜ | 3.1.12 | **version_compare** — port (pair-level); `analyze(doc_a, doc_b)` over two `PerceptionDocument`s → producer-fingerprint deltas. Stays a standalone tool/view. | 🟢 python-eng |
| ⬜ | 3.1.13 | ☁️ **BUILD CHECK (Wave 2)** — ⚫ Lead runs full Python suite over all 24 moved modules. Cloud-offloadable. | ⚫ Lead |

### 3.2 Track C — FastAPI sidecar (concurrent)

> ✅ **Done — `api/{app,sse,routes/jobs,routes/library}.py` + `tests/api/` green.** Lifespan warms
> **audio-separator + faster-whisper** (NOT demucs/whisper — those were removed); tests use httpx
> `ASGITransport` (not the deprecated `TestClient`).

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 3.2.1 | **`api/app.py`** — FastAPI instance + **lifespan that warms demucs + whisper once** (the multi-minute speedup). In-memory job registry + per-job working dir; single GPU worker (jobs serialize). | 🟢 python-eng |
| ⬜ | 3.2.2 | **`api/routes/jobs.py`** — `POST /jobs` (start analysis on a local path), `GET /jobs/{id}`, `GET /jobs/{id}/perception` (serves the `PerceptionDocument`). REST per `api-design.md` (snake_case JSON, consistent error shape, no auth — local tool). | 🟢 python-eng |
| ⬜ | 3.2.3 | **`api/sse.py`** — SSE stream `GET /jobs/{id}/events` emitting `ProgressEvent`s (21 stages) from the orchestrator. | 🟢 python-eng |
| ⬜ | 3.2.4 | **`api/routes/library.py`** — `GET /library` (paginated tracks from DuckDB), `GET /library/{id}/twins` (VSS twin-search via `db/twins.py`). | 🟢 python-eng |
| ⬜ | 3.2.5 | **API tests + BUILD CHECK** — `tests/api/` with FastAPI `TestClient`/httpx: job lifecycle, SSE event sequence, library + twins. `uv run mypy src/claudes_ears/api && pytest tests/api` clean. | 🟢 python-eng |

### 3.3 Track B — Library metadata wiring (concurrent)

> ✅ **Done — `db/library.py` metadata upsert (`get_track_metadata`) + `db/twins.py` HNSW twin-search; 16 tests green.**

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 3.3.1 | **Metadata columns (ISSUE-014)** — `db/library.py` upserts the per-track era/year/artist/genre metadata columns; expose a query for `temporal_genome` to consume real metadata. | 🟠 db-eng |
| ⬜ | 3.3.2 | **BUILD CHECK** — `uv run pytest tests/db` clean incl. metadata round-trip. | 🟠 db-eng |

### 3.4 Track D — Perception report + library views (concurrent, mock-bound until P4)

> **Design system first.** `.project/design/` is the authority: `design-system.md` (tokens, type,
> components, ASCII layouts, flows, states), `tokens.css` (Tailwind v4 `@theme`), `palette.html` +
> `app-shell.html` (approved visual refs). Linear-derived cold-dark, no cyan, 6-voice taxonomy.

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ✅ | 3.4.0 | **Design system** — tokens + type + components + ASCII layouts + launch/shell flows; approved visual refs. Replaces the cyan `@theme`. | 🔵 react-eng + 🎨 |
| ✅ | 3.4.1 | 🎨 **Voices tab (headline)** — beeswarm of `solo/support/dialogue/opposition/merge/withdraw` over the shared time axis + distribution + register/breath + story line. | 🔵 react-eng + 🎨 |
| ✅ | 3.4.2 | **Harmony + Structure + Space views** — chord ribbon/roman/cadences, sections + valence/arousal on the shared spine, stereo×depth field. | 🔵 react-eng |
| ✅ | 3.4.3 | **AI lens + Story views** — self-opposition read (lens, not verdict) + grounded reading in Fraunces. | 🔵 react-eng |
| ✅ | 3.4.4 | **Library tab (placeholder)** — designed track-browser + genome-fingerprint twins shape; lights up on real DuckDB in P4. | 🔵 react-eng + 🎨 |
| ✅ | 3.4.5 | **Desktop BUILD CHECK** — typecheck/lint/test 13/build green; all 7 tabs render vs mock; four states designed. | 🔵 react-eng |
| ✅ | 3.4.6 | **App shell (Library sidebar + workspace frame)** — persistent shell (`components/shell/`): titlebar (search/⌘K/Add), Library sidebar (`library-store`, newest-first, URL `?track=`), drop target in-pane. Tests 13→27 (tab smokes + shell integration + store). | 🔵 react-eng + 🎨 |

---

## Gate G3: Window 2 Merge — ✅ committed a1ab948 (review deferred)

> **Status:** user chose **commit-now / review-after**. Window 2 committed + pushed (`51e508e..a1ab948`),
> all suites green. The adversarial `code-review-engineer` pass was **deferred by the user** — run it
> later before the PR is finalized.
>
> **Current direction → Frontend Polish (interlude).** Iterative renderer polish until the user is happy
> with the look, *before* Phase 4. Dev upload uses **mock data** (real analysis is Phase 4); the user
> needs the upload flow to function so they can click through. Active polish items: fix `crypto.randomUUID`
> crash on upload (`lib/api.ts`), remove the redundant central drop card (the titlebar + sidebar
> `+ Add track` buttons are the entry points), keep iterating per user feedback.

### Prerequisites
- [x] All Wave-2 modules done (issues 003, 004, 005, 009, 011, 014 closed; 008/012/013 mechanisms complete)
- [x] API, library metadata, and renderer views (+ app shell) signaled completion

### Gate Protocol
1. ⚫ Lead summarizes per-agent changes; lists issues now closeable.
2. 🔴 code-review-engineer reviews the merged window (API security/shape per `api-design.md`, renderer state doctrine per `react.md`).
3. **USER REVIEWS AND APPROVES — no auto-proceed.**
4. ⚫ Lead runs full Python + desktop suites; fixes fallout; merges deps; regenerates locks.
5. ⚫ Lead commits + pushes; moves closed issues; updates changelog.

### Conflict Resolution Priority
1. `models/` canonical; 2. `pyproject.toml`/`uv.lock`; 3. API contract vs `lib/api.ts` Zod — schema.md wins.

---

## Phase 4: Integration

> **Sequential. ⚫ Lead-coordinated**, 🟢 python-eng + 🔵 react-eng. Now wire the **real** end-to-end
> on a sample track and close the structural issues for good. No new features — connect what exists.

### 4.1 End-to-end pipeline wiring

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 4.1.1 | **Real run** — run `orchestrator` on a real audio file: separation → 24 `analyze()` → consolidator → `PerceptionDocument`. Fix any raw-shape mismatch against `schema.md` §2 discovered against real outputs. | 🟢 python-eng |
| ⬜ | 4.1.2 | **Verify degraded paths (ISSUE-008)** — force a failed/degraded step (e.g. missing stem, short audio, mono, `{error}` emotion) and assert the domain serializes as `null`, never a missing key or `{error}` blob. | 🟢 python-eng |
| ⬜ | 4.1.3 | **Index the doc** — consolidator output upserts into DuckDB (`tracks` + `genome_vectors`); twin-search returns sane neighbours on a 2–3 track set. Verify genome vector persisted (schema finding #4). | 🟢 python-eng |
| ⬜ | 4.1.4 | **Capture semantic_lyrics (ISSUE-012) + env unification (ISSUE-007)** — confirm the in-process orchestrator captures the VADER+LLM result into `lyrics`, and all stem I/O honors `config.py`. | 🟢 python-eng |
| ⬜ | 4.1.5 | **Remove dead root scripts** — delete `full_perception.py`, `run_demucs.py`, and any leftover root `*.py` now living under `src/` (**ISSUE-001** root cause gone — no shell, no subprocess). | ⚫ Lead |
| ⬜ | 4.1.6 | **Wire metadata → temporal_genome (ISSUE-014 finish)** — `db/get_track_metadata` is defined but never invoked at runtime; feed real per-track `{year, genre, era, artist}` into `temporal_genome.analyze()` so era/genre clustering reads DuckDB columns, not nothing. (Audit gap.) | 🟢 python-eng |

### 4.2 Desktop ↔ sidecar wiring

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 4.2.1 | **Electron spawns the sidecar** — `electron/main.ts` spawns + supervises the FastAPI (uvicorn) process; preload bridges native file dialogs/drag-drop; renderer talks **real** localhost HTTP/SSE (drop mock). | 🔵 react-eng |
| ⬜ | 4.2.2 | **Live progress + real report** — drop a track → live 21-stage SSE progress → consolidated report renders from the real `PerceptionDocument`. | 🔵 react-eng |
| ⬜ | 4.2.3 | **Library + twins live** — library view reads real DuckDB; sonic-twins works against analyzed tracks. | 🔵 react-eng |

### 4.3 Cross-cutting + docs

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 4.3.1 | **Doc reconcile (ISSUE-013)** — update README / CLAUDE.md / prd: `semantic_lyrics` owns the grounded LLM reading, `story_reader` is rule-based synthesis. | ⚫ Lead |
| ⬜ | 4.3.2 | **BUILD CHECK** — full Python + full desktop suites green; manual smoke: one real track end-to-end in the app. | ⚫ Lead |

### 4.4 Library management & robustness (audit-surfaced 2026-06-30)

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 4.4.1 | **Frontend library hydrate** — replace job-completion-only seeding with a TanStack Query hydrate against `GET /library`; persist selection. Library survives reload. (`library-store.ts` comment already plans this.) | 🔵 react-eng |
| ⬜ | 4.4.2 | **Track CRUD endpoints + UI** — add `GET /library/{id}` (track detail, currently only `/twins` exists), `PATCH` (rename/edit metadata), `DELETE` (remove track + genome row + perception.json). Wire rename/delete affordances into `LibrarySidebar`. | 🟢 python-eng + 🔵 react-eng |
| ⬜ | 4.4.3 | **Job persistence + list/cancel** — jobs are in-memory; a sidecar restart orphans running/completed status (DB row survives, job doesn't). Add `GET /jobs` (list), cancel/delete, and durable job state. | 🟢 python-eng |
| ⬜ | 4.4.4 | **Data-dir resolution** — `library.duckdb` defaults CWD-relative; resolve to a stable per-user app data dir (honor `CLAUDES_EARS_LIBRARY`, packaged-app safe). Same for `work_dir`. | 🟢 python-eng + ⚙️ devops |
| ⬜ | 4.4.5 | **Ingest path decision** — `POST /jobs` takes a sidecar-local `audio_path` only (no upload). For the local desktop app this is fine via the Electron picker bridge; confirm the contract and document it (no HTTP upload endpoint needed for a single-user local tool). | ⚫ Lead |
| ✅ | 4.4.6 | **YouTube URL ingest** — `POST /jobs` accepts exactly one of `audio_path` \| `source_url`; sidecar downloads via yt-dlp into the music dir (download progress as a `download` SSE step before the pipeline), then runs the normal pipeline. yt-dlp was a declared dep with no feature. | 🟢 python-eng |
| ✅ | 4.4.7 | **Add-track modal + live dashboard** — mock retired (`VITE_USE_MOCK` default false); library hydrates from `GET /library` (subsumes 4.4.1); titlebar Add opens a modal: "From YouTube" (URL) \| "Upload" (file picker/path); dashboard of prior songs. `frontend-design` drives visual direction. | 🔵 react-eng |

---

## Gate G4: Integration Complete

### Prerequisites
- [ ] Real track flows drop → analyze → report → library end-to-end
- [ ] ISSUE-001/007/008/012/013 verified closed; dead root scripts removed

### Gate Protocol
1. ⚫ Lead demos the end-to-end flow to the user. 2. 🔴 code-review-engineer full-system review.
3. **USER REVIEWS AND APPROVES.** 4. ⚫ Lead commits + pushes; updates changelog; closes issues.

---

## Phase 5: Hardening 🤝

> **PARALLEL — agent team.** Depends on: G4 (working end-to-end). Independent boundaries: tests vs
> review vs packaging-prep. Heavily cloud-eligible (deterministic suites).

### File Ownership (This Phase)

| Agent | Owns | Reads only |
| ----- | ---- | ---------- |
| 🟣 qa-eng | `tests/**` (integration, E2E, golden fixtures, hazard tests) | all `src/` |
| 🔴 code-review-eng | review reports + issue filings | all |
| ⚙️ devops-eng | `pyinstaller/`, `desktop/electron-builder.yml` (prep only) | all |

### 5.1 Test coverage + review

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 5.1.1 | ☁️ **Golden `PerceptionDocument` fixture + E2E** — full pipeline on a checked-in sample clip; snapshot the consolidated doc; assert schema_version + all-domains-present-or-null. | 🟣 qa-eng |
| ⬜ | 5.1.2 | ☁️ **Hazard test matrix** — NaN inputs, <3-snapshot short audio, mono file, `<2` stems, degraded emotion JSON, present-but-zero tempo (the schema §5 hazards) all yield valid JSON / typed nulls. | 🟣 qa-eng |
| ⬜ | 5.1.3 | ☁️ **API + SSE integration tests** — job lifecycle, SSE ordering/completion, library pagination, twin-search correctness. | 🟣 qa-eng |
| ⬜ | 5.1.4 | **Renderer E2E** — drop→progress→report happy path + the four component states; `prefers-reduced-motion` honored. | 🟣 qa-eng |
| ⬜ | 5.1.5 | ☁️ **Adversarial review** — `code-review-engineer` sweeps the full diff: type lies, swallowed errors, boundary violations, dependency hygiene. File any findings as new issues. | 🔴 code-review-eng |
| ⬜ | 5.1.6 | **BUILD CHECK** — full suites green; coverage gate met. | 🟣 qa-eng |

### 5.2 Packaging prep (concurrent, non-blocking)

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 5.2.1 | **PyInstaller spec (draft)** — author the sidecar freeze spec: torch/demucs/whisper hidden imports, data files, bundled weights (whisper `base` ~145 MB + demucs `htdemucs` ~80 MB). Dry-run build. | ⚙️ devops-eng |
| ⬜ | 5.2.2 | **Electron Builder config (draft)** — `electron-builder.yml`: bundle the frozen sidecar, Mac + Win targets, weight assets. No signing yet. | ⚙️ devops-eng |

---

## Gate G5: Hardening Complete

### Prerequisites
- [ ] All test suites green; coverage gate met; review findings triaged (filed or fixed)
- [ ] PyInstaller + Electron Builder drafts produce a runnable dev bundle

### Gate Protocol
1. ⚫ Lead summarizes coverage + open findings. 2. **USER REVIEWS AND APPROVES.**
3. ⚫ Lead commits + pushes; files/closes issues; updates changelog.

---

## Phase 6: Packaging & Release

> **Sequential. ⚙️ devops-eng, ⚫ Lead-coordinated.** The real "desktop" engineering cost — freeze
> the ML payload cross-platform, sign, and ship installers. Depends on: G5.

### 6.1 Freeze, sign, ship

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 6.1.1 | **Finalize PyInstaller sidecar** — reproducible freeze from `uv.lock` on macOS and Windows; verify warm-model load inside the frozen binary; bundled weights resolve offline. | ⚙️ devops-eng |
| ⬜ | 6.1.2 | **Electron Builder packaging** — produce `.dmg` (Mac) + installer (Win) embedding the frozen sidecar + weights. | ⚙️ devops-eng |
| ⬜ | 6.1.3 | **Code-sign + notarize (Mac)** — sign + notarize; verify Gatekeeper passes. Secrets via env/keychain, never committed (`security.md`). | ⚙️ devops-eng |
| ⬜ | 6.1.4 | **Sign (Windows)** — Authenticode sign the installer; verify SmartScreen behavior. | ⚙️ devops-eng |
| ⬜ | 6.1.5 | ☁️ **Installer smoke test (both OSes)** — clean-machine install → drop a track → full report renders offline. Deterministic pass/fail. | ⚙️ devops-eng |
| ⬜ | 6.1.6 | **Release notes + changelog** — ⚫ Lead writes release notes; final changelog entry; tag. | ⚫ Lead |

### 6.2 Final verification

| Status | Task | Description | Agent |
| ------ | ---- | ----------- | ----- |
| ⬜ | 6.2.1 | **Full release verification** — full Python + desktop suites + signed-installer smoke on macOS and Windows, all green. | ⚫ Lead |
| ⬜ | 6.2.2 | **All issues closed/triaged** — confirm ISSUE-001..014 resolved or explicitly deferred with rationale. | ⚫ Lead |

---

## Gate G6: Release (Final)

### Prerequisites
- [ ] Signed/notarized installers smoke-tested on macOS + Windows
- [ ] All suites green; ISSUE-001..014 resolved or deferred-with-rationale

### Gate Protocol
1. ⚫ Lead presents the release candidate + verification evidence. 2. 🔴 final review. 3. **USER APPROVES.**
4. ⚫ Lead tags + ships; updates changelog; archives the build plan.

---

## Parallelization Map

```
Phase 1: FOUNDATION (sequential — ⚫ Lead, 🟢, 🟠) ── the frozen contract
  1.1 scaffold/pyproject/config/_sanitize ─→ 1.2 models (PerceptionDocument, GenomeVector, jobs)
        ─→ 1.3 steps.py + 24 analyze() stubs + cli ─→ 1.4 decisions(013,014) + db/schema.sql
  │
  ▼ ═══════════════════ GATE G1 (user approval — CONTRACT FROZEN) ═══════════════════
  │
Phase 2: PARALLEL WINDOW 1 🤝  (four tracks concurrent, ~16 agents)
  ├─ Track A  Module Wave 1 ── 🟢×12 ──┐   separation, analyze_stems, vocal_intervals(010),
  │                                     │   vocal_narrative(002), relationships, layers, register,
  │                                     │   breath, groove, freq_interaction, timbral(006), chords
  ├─ Track B  DuckDB layer ── 🟠 ───────┤   library.py + twins.py (VSS, 12-dim)
  ├─ Track C  Consolidator+Orchestrator ┤   in-process (kills 001); genome vector persist; ISSUE-008/012 capture
  └─ Track D  Desktop shell ── 🔵+🎨 ───┤   scaffold, lib/api.ts (Zod), drop-zone, 21-stage progress (mock)
  │                                     ▼
  ▼ ═══════════════════ GATE G2 (user approval — Lead build/lint/test, commit) ═══════════════════
  │
Phase 3: PARALLEL WINDOW 2 🤝  (builds on G2 — four tracks concurrent)
  ├─ Track A  Module Wave 2 ── 🟢×12 ──┐   stereo(004), temporal(005), depth, music_theory(003),
  │                                     │   harmonic_rhythm(011), emotion(005), semantic_lyrics(009,012),
  │                                     │   story_reader(008), ai_detector, genome_map, temporal_genome(014), version_compare
  ├─ Track C  FastAPI sidecar ── 🟢 ────┤   warm models; /jobs; SSE; /library + /twins
  ├─ Track B  metadata columns ── 🟠 ───┤   ISSUE-014 wiring
  └─ Track D  report + library views ─🔵+🎨┤  vocal-relationship timeline, harmony/emotion, AI/story, twins
  │                                     ▼
  ▼ ═══════════════════ GATE G3 (user approval) ═══════════════════
  │
Phase 4: INTEGRATION (sequential — 🟢 + 🔵, ⚫ coord)
  real run → fix shapes → degraded=null(008) → index → electron spawns sidecar → live report → docs(013)
  │
  ▼ ═══════════════════ GATE G4 (user approval) ═══════════════════
  │
Phase 5: HARDENING 🤝  (🟣 tests ∥ 🔴 review ∥ ⚙️ packaging-prep — cloud-eligible)
  │
  ▼ ═══════════════════ GATE G5 (user approval) ═══════════════════
  │
Phase 6: PACKAGING & RELEASE (sequential — ⚙️, ⚫ coord)
  PyInstaller freeze → Electron Builder → sign+notarize(Mac) / sign(Win) → installer smoke (both OSes)
  │
  ▼ ═══════════════════ GATE G6 (user approval — FINAL) ═══════════════════
```

**Critical path:** Foundation contract → (any one Window-1 track) → Window-2 dependent work
(API needs consolidator+db; renderer views need the shell) → Integration (real wiring, the
serialization point) → Hardening → Packaging. The 24-module fan-out is **off** the critical path —
it parallelizes into the windows and is gated by Lead build checks, not by other modules.

---

## Changelog Reference

See `.project/changelog.md` (⚫ Lead updates at each gate/milestone).

---

## Notes & Decisions

### Foundation Decisions (recorded at G1 — 2026-06-30)
- **1.4.1 — LLM ownership (ISSUE-013).** `semantic_lyrics` owns the grounded LLM (Claude API) call:
  the model `LyricsAnalysis` holds VADER (`vader`) + the LLM `semantic` block + `interpretation_gap`.
  `story_reader` stays **rule-based** synthesis over upstream dicts and maps to `StoryReading`
  (no LLM). Doc reconciliation (README/CLAUDE.md/prd) scheduled in P4 (4.3.1). The current code calls
  `claude-sonnet-4-20250514`; the model id is revisited in 3.1.7 against the `claude-api` reference.
- **1.4.2 — track metadata (ISSUE-014).** `year`/`genre`/`era` (+ `title`/`artist`) are real per-track
  metadata: columns on DuckDB `tracks` **and** fields on `TrackMeta`. `temporal_genome.analyze()` takes
  a `metadata` param (no hardcoded `METADATA` dict). Columns agreed: `year INTEGER, genre TEXT, era TEXT`.
- **Deviation — dependency split (for G1 review).** The plan listed the whole ML tree as runtime deps.
  Implemented as: core app/contract deps in `[project.dependencies]` (pydantic, fastapi, uvicorn,
  sse-starlette, duckdb, httpx, numpy, scipy) and the heavy DSP/CUDA stack (torch, torchaudio, demucs,
  librosa, soundfile, scikit-learn, openai-whisper, vaderSentiment, yt-dlp, ffmpeg-python) in an
  optional `ml` extra (`uv sync --extra ml`). Rationale: keep `uv run` (which auto-syncs) light for
  contract/API/DB work; never force a multi-GB GPU install to type-check a Pydantic model. Foundation
  code imports none of the ML tree. **Reversible — flag if you want them unified for PyInstaller.**
- **Deviation — verify scope (`src tests`).** ruff's exclude globs match by basename and `*` spans
  path separators, so there is no root-only exclude that spares the same-named `src/` file during the
  fan-out. The canonical Python verify therefore scopes ruff to `src tests` (mypy via `files` + a
  path-anchored exclude). Legacy root scripts migrate into scope file-by-file as modules port.
- **DDL split.** `db/schema.sql` holds the table DDL (idempotent `CREATE TABLE IF NOT EXISTS`); the
  HNSW/VSS index is created/refreshed by `db/twins.py` after `LOAD vss` + the experimental-persistence
  pragma (index DDL is invalid before the extension loads). 🟠 db-eng owns the index in Window 1 (2.2.2).
- **Reserved-word aliases.** Module keys `from` / `class` / `register` collide with Python /
  `ABCMeta.register`; modeled as `from_` / `class_` / `register_` with `alias=` + `populate_by_name`.
  Canonical JSON round-trips via `model_dump(by_alias=True)`.

### G1 contract-review fixes (folded in before freeze)
Adversarial review graded the contract **A− / sound to freeze**; these were closed pre-commit:
- **Multi-upstream dict key contract.** The aggregating dict an `UPSTREAM`/`STEM_DIR`-derived step
  receives (`context`, `vocal_outputs`) is **keyed by `depends_on` step name** — pinned on
  `InputKind.UPSTREAM` and documented in each derived stub. Track C orchestrator must key by step name.
- **Genome all-or-nothing.** `PerceptionDocument.genome` is `None` unless **all 12 dims are finite**;
  the consolidator (2.3.2) must not partial-fill (it silently skews twin-search). Pinned in the model.
- **Registry validator.** `_validate_registry()` now also enforces topological order, the
  `ORCHESTRATED_STEP_COUNT == 21` SSE-total invariant, and phase/orchestration coherence — fails at import.
- Minors: `_sanitize` docstring no longer over-claims "JSON-safe"; `ProgressEvent.index/total` are `ge=1`.

### Architecture Decisions
- **Contract-first, freeze-then-fan-out.** `models/perception.py` + `steps.py` + `db/schema.sql` are
  authored and frozen in Foundation (G1). Everything downstream binds to them; changes force a re-gate.
- **24 analyze() stubs in Foundation.** Stubs make the registry, orchestrator, and consolidator
  type-check at G1 and let the fan-out replace one body per agent with zero import breakage.
- **The module fan-out is the parallelism engine.** Each of 24 modules is a one-file unit
  (move + extract `analyze()` + fix issue + type hints + test). Two waves of 12 (Window 1 / Window 2).
- **Derived modules take upstream dicts, not sibling-JSON paths** — kills the filename-replace
  fragility hazard (schema §5) and the hard-indexed-contract bug class at the source.
- **In-process orchestrator replaces subprocess `full_perception.py`** — warm models once, no shell
  (the ISSUE-001 root fix), clean under PyInstaller.
- **Genome vector is computed in the consolidator and persisted** to `PerceptionDocument.genome` +
  DuckDB `genome_vectors` (schema finding #4 — today it evaporates after `genome_map`).
- **ISSUE-013:** `semantic_lyrics` owns the grounded LLM (Claude API) reading; `story_reader` is
  rule-based. **ISSUE-014:** track metadata → DuckDB columns, passed into `temporal_genome.analyze()`.
- **No hosting/queue/auth/server-DB** — single-user local tool. In-memory job registry; one GPU
  serializes jobs; SSE for progress; DuckDB embedded; no CORS/auth on the localhost sidecar.

### Parallelization Accounting
- **Sequential (critical path):** Foundation (12 tasks), Integration (12), Packaging (10) ≈ 34 tasks.
- **Parallelizable:** the two windows ≈ 60 tasks across 4 concurrent tracks (24-module fan-out is the
  bulk), plus Hardening (12) across 3 boundaries.
- Cloud-eligible (☁️): wave build-checks, hazard/API test suites, installer smoke — deterministic
  success criteria, no in-flight dependencies.

### Known Issues
- ISSUE-001..014 mapped to phases (see Issue Integration Map). 002/006/007/010 close in Window 1;
  003/004/005/009/011/014 in Window 2; 001/008/012/013 are structural and verified in Integration.

### Conflict Zone Incidents
- _(log any merge collisions or boundary violations here for future reference)_

---

_Last updated: 2026-06-30 (full-stack audit + Phase 4 scope widened)_
_Current Phase: Phases 1–3 complete (a1ab948); Frontend Polish interlude (crypto/dropzone fixes landed, uncommitted)_
_Next Milestone: Phase 4.1.1 — first real audio run through the orchestrator (blocked on a real song)_
