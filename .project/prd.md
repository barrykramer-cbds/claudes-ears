# Claude's Ears — Product Requirements Document

## Overview

### Problem Statement
Most music-analysis tooling stops at feature extraction — chroma, MFCC, tempo, key, beats. The broader ecosystem does measurement and source separation well, and a mature industry does forensic AI-music detection. None of them ask what the voices are *saying to each other*, what a producer *did* to an arrangement, or what *story* a song carries.

### Solution
A 25-module Python audio perception pipeline that uses feature extraction and stem separation as a substrate and builds an interpretive layer on top. It occupies the space that MIR tooling and forensic detectors deliberately avoid.

### Target Users
- **Primary:** Music analysts, researchers, and producers who want interpretive insight beyond feature metrics
- **Secondary:** Engineers and academics studying vocal relationships, producer fingerprints, and AI-generated vocal detection

---

## Core Features

### Vocal Relationship Taxonomy
**Priority:** P0

Classifies how simultaneous voices relate moment-to-moment: `solo / support / dialogue / opposition / merge / withdraw`. Not a single "vocals" blob — a dynamic relational map over time.

**Module:** `vocal_relationships.py`

---

### Producer Fingerprint Detection
**Priority:** P0

Given a studio and a live version of the same song, quantifies the delta across every measured dimension. That delta *is* the producer's invisible hand — what was added, buried, or imposed on the performer.

**Module:** `version_compare.py`

---

### Architectural AI Voice Detection
**Priority:** P0

Does not hunt spectral artifacts or watermarks. Asks a structural question: does the voice *argue with itself* (self-opposition, characteristic of human performance) or *agree with itself* (self-reinforcement, characteristic of generated vocals)?

**Honest limitation:** At the top end of studio production, heavily-produced human pop and AI-generated music converge on the same commercial polish. This detector characterizes vocal *personality and architecture* — it is a lens, not a verdict.

**Module:** `ai_detector.py`

---

### Grounded Story Reading
**Priority:** P0

Feeds measured acoustic data (vocal relationships, harmonic function, emotional trajectory) *plus* transcribed lyrics into an LLM for lyric-aligned musical analysis. Inverts the standard assumption that a model "cannot hear."

**Module:** `story_reader.py`

---

### Full Perception Pipeline
**Priority:** P0

Orchestrates all modules in sequence across 5 phases: stem separation → stem analysis → full mix → derived/semantic → cross-track library. Supports single-track, `--skip-demucs`, and `--batch` modes.

**Module:** `full_perception.py`

---

### Cross-Track Library (Genome / Temporal)
**Priority:** P1

Maps acoustic DNA across a track library to find sonic twins, cross-era relationships, and arrangement echoes.

**Modules:** `genome_map.py`, `temporal_genome.py`

---

## Application Layer — Desktop App

> The pipeline already works; its output is ~20 scattered JSON files no human can consume. This
> phase makes the perception **legible and experiential** — a cross-platform desktop app (Mac +
> Windows) that turns the existing analysis into something you can drop a track into and *read*.
> Personal local tool, not hosted. See `tech-stack.md` for architecture.

### Drag-and-drop analysis
**Priority:** P0

Drop an audio file (or point at a folder) → the pipeline runs locally with **live progress**
(per-step, 21 stages) → a consolidated perception report appears. Native file access, no upload.

> As a listener, I want to drop a song in and watch it get "heard," so I get the full reading without touching a command line.

### The perception report
**Priority:** P0

One consolidated, readable view per track built from the `PerceptionDocument`: the vocal-relationship
story over time, harmonic function, emotional trajectory, the AI-detection read, and the grounded
story reading — the *interpretation*, surfaced, not raw JSON. In-app rendering (no export in v1).

### Library & sonic twins
**Priority:** P1

Browse every analyzed track; find **sonic twins** and cross-era relationships via similarity search
over the genome vectors (DuckDB VSS). Instant — reads the existing index, no re-analysis.

### Foundation refactor (enabling work)
**Priority:** P0 (technical prerequisite)

The 24 standalone scripts become an importable package with `analyze(path) -> dict` functions, a
typed `PerceptionDocument` contract, a consolidation step, and a warm-model FastAPI sidecar. Not a
rewrite — a refactor + reorganize of working code. Also closes the open correctness/security issues
(`ISSUE-001`…`011`) as each module is touched.

---

## Design Principles

1. The music is the vessel; the story is what it carries. Never prioritize measurement over meaning.
2. A solo is a vocal spotlight — the performer's personality demanding the stage. Expression, not vulnerability.
3. Measurement is not listening. Numbers describe what happened; listening hears why.
4. The arrangement is a negotiation between performer and producer. The recording freezes the outcome.
5. Personality drives architecture.

---

## Out of Scope

- Forensic AI-music watermark/artifact detection (explicitly deferred — different problem)
- Real-time audio processing
- DAW plugin
- Streaming input
- Hosted/SaaS deployment, multi-user, cloud GPU (personal local tool only)
- Standalone report export (HTML/PDF) — in-app rendering only for v1

---

*Last updated: 2026-06-30*
