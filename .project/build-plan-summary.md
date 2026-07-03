# Build Plan Summary — Claude's Ears

> Orientation for future sessions. Full plan: `.project/build-plan.md`. Contract: `.project/schema.md`.

## What the plan delivers
Refactor a 24-module flat Python audio pipeline into an Electron desktop app: importable
`analyze(...) -> dict` package (`src/claudes_ears/`) behind a warm-model FastAPI sidecar → typed
`PerceptionDocument` → DuckDB index (VSS twins) → React/Vite/Tailwind/shadcn UI (Emil polish) →
PyInstaller + Electron Builder. Local single-user tool — no hosting/queue/auth/server-DB.

## Key architectural decisions
- **Contract-first, freeze-then-fan-out.** Foundation authors and freezes `models/perception.py`
  (`PerceptionDocument`, every domain `| None`), `pipeline/steps.py` (registry + `analyze()`
  signatures), `db/schema.sql` (tracks + `genome_vectors FLOAT[12]` + VSS), `config.py`, `_sanitize.py`.
  Frozen at G1; changes force a re-gate. Everything downstream binds to these.
- **24 `analyze()` stubs created in Foundation** so the registry/orchestrator/consolidator type-check
  at G1; the fan-out replaces one stub body per agent — zero import breakage.
- **Module fan-out is the parallelism engine.** Each module = one-file unit (move root→`analysis/`,
  extract `analyze()`, fix its issue, type hints, unit test). Two waves of 12 (Windows 1 & 2).
- **Derived modules take upstream dicts, not sibling-JSON paths** (kills the filename-replace hazard
  and the hard-indexed-contract bug class).
- **In-process orchestrator replaces subprocess `full_perception.py`** (warm models, no shell — the
  ISSUE-001 fix, clean under PyInstaller).
- **Genome vector computed in the consolidator and persisted** (schema finding #4 — today it evaporates).
- **ISSUE-013:** `semantic_lyrics` owns the Claude API reading; `story_reader` is rule-based.
  **ISSUE-014:** track metadata → DuckDB columns, passed into `temporal_genome.analyze()`.

## Phase structure (6 phases, 6 gates, ~106 tasks)
1. **Foundation** (sequential, ⚫🟢🟠) — frozen contract → **G1**.
2. **Parallel Window 1** 🤝 — Module Wave 1 (12) + DuckDB layer + consolidator/orchestrator + desktop shell → **G2**.
3. **Parallel Window 2** 🤝 — Module Wave 2 (12) + FastAPI sidecar + metadata + report/library views → **G3**.
4. **Integration** (sequential) — real end-to-end wiring, degraded=null verify, electron spawns sidecar → **G4**.
5. **Hardening** 🤝 — qa tests ∥ adversarial review ∥ packaging prep → **G5**.
6. **Packaging & Release** (sequential, ⚙️) — PyInstaller freeze, Electron Builder, sign/notarize, installer smoke → **G6**.

## Critical path vs parallel
- **Critical path:** Foundation → one Window-1 track → Window-2 dependent work (API needs
  consolidator+db; views need shell) → Integration (the serialization point) → Hardening → Packaging.
- **Off critical path:** the 24-module fan-out (parallelizes into the windows; gated by Lead builds).
- ~34 sequential tasks; ~60 parallelizable across the two windows + 12 hardening across 3 boundaries.

## Agents / dots
🟢 python-engineer (one instance per module in fan-out) · 🟠 database-engineer · 🔵 react-engineer
(+🎨 emil-design-eng skill) · 🟣 qa-engineer · 🔴 code-review-engineer · ⚙️ devops-engineer · ⚫ Lead.

## Gotchas
- No `.claude/rules/orchestration.md` exists in the repo (referenced by the architect brief but absent);
  gate protocol is embedded in the build plan from the template.
- All gates require **user approval**; agents never commit/push (⚫ Lead owns git + `.project/`).
- Conflict zones (frozen during windows): `pyproject.toml`/`uv.lock`, `models/`, `steps.py`,
  `db/schema.sql`, `config.py`, `_sanitize.py`, `cli.py`, `desktop/package.json`, `.project/`.

_Last updated: 2026-06-30_
