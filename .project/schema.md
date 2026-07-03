# Claude's Ears — Data Schema

> **Source of truth for the `PerceptionDocument` consolidation + DuckDB index.** Built by reading
> the actual `json.dump` sites of all 24 modules (not inferred). Field types reflect what the code
> emits today, including its quirks. The consolidator's job is to normalize these into one typed,
> validated document. `build-plan-architect` should treat the **Hazards** and **Build-relevant
> findings** sections as concrete requirements.
>
> *Mapped 2026-06-30.*

---

## 1. Module output inventory

| Module | Output artifact | Persists? | Consumes | Encoder | Grain |
|---|---|---|---|---|---|
| `analyze_stems` | `<stem_dir>/stem_analysis.json` | ✅ | stem dir (4 wavs) | manual cast | per-track |
| `vocal_layers` | `<base>_layers.json` | ✅ | vocals.wav | manual | per-track |
| `vocal_intervals` | `<base>_intervals.json` | ✅ | vocals.wav | manual | per-track |
| `vocal_narrative` | `<base>_narrative.json` | ✅ | vocals.wav | NpEncoder | per-track |
| `vocal_relationships` | `<base>_relationships.json` | ✅ | vocals.wav | NpEncoder | per-track |
| `register_tracking` | `<base>_register.json` | ✅ | vocals.wav | NpEncoder | per-track |
| `breath_detection` | `<base>_breath.json` | ✅ | vocals.wav | NpEncoder | per-track |
| `groove_timing` | `<base>_groove.json` | ✅ | drums.wav / mix | manual | per-track |
| `freq_interaction` | `<stem_dir>/freq_interaction.json` | ✅ | stem dir | manual | per-track |
| `timbral_decomposition` | `<base>_timbral.json` | ✅ | other.wav | NpEncoder | per-track |
| `chord_progression` | `<base>_chords.json` | ✅ | full mix | manual | per-track |
| `harmonic_rhythm` | `<base>_harmonic_rhythm.json` | ✅ | `_chords.json` | NpEncoder | per-track |
| `music_theory` | `<base>_theory.json` | ✅ | `_chords.json` | NpEncoder | per-track |
| `stereo_field` | `<base>_stereo.json` | ✅ | full mix | manual | per-track |
| `temporal_segmentation` | `<base>_temporal.json` | ✅ | full mix | manual | per-track |
| `depth_reverb` | `<base>_depth.json` | ✅ | full mix | manual | per-track |
| `emotional_trajectory` | `<base>_emotion.json` | ✅ | `_temporal.json` | manual | per-track |
| `semantic_lyrics` | **— prints only —** | ❌ | lyrics.ovh + Claude API | — | per-track |
| `story_reader` | `<base>_story.json` | ✅ | many sibling JSONs + whisper | NpEncoder | per-track |
| `ai_detector` | `<stem_dir>/ai_detection.json` (or array in `--batch`) | ✅ | 4 sibling JSONs | NpEncoder | per-track |
| `genome_map` | `<stems>/genome_map.json` | ✅ | all `stem_analysis.json` | manual | **library** |
| `temporal_genome` | `<stems>/temporal_genome.json` | ✅ | `genome_map.json` + hardcoded METADATA | manual | **library** |
| `version_compare` | `comparison_<A>_vs_<B>.json` | ✅ | both tracks' JSONs | NpEncoder | **pair** |

**Universal join key:** raw demucs stem-folder name (a string), used across `stem_analysis → genome_map → temporal_genome`. String equality only — fragile.

---

## 2. PerceptionDocument (per-track) — field mapping

One document per track, assembled by the consolidator from the per-track artifacts above.
Library- and pair-level artifacts (`genome_map`, `temporal_genome`, `version_compare`) are **separate** — see §4.

```
PerceptionDocument
├── schema_version: str                      # NEW — no module emits one today; consolidator adds it
├── track: TrackMeta                         # derived: id(=stem folder), title, artist, source_path,
│                                             #   duration, sample_rate, analyzed_at, pipeline_version
│
├── separation: { stems_present: [str], stem_dir: str }       # from disk / run_demucs
│
├── stems: (from analyze_stems — every sub-key OPTIONAL, present only if that stem file existed)
│   ├── vocals: { duration, pitch_mean_hz?, pitch_range_semitones?, voiced_fraction?,
│   │            vocal_melodic_entropy?, breathiness, breathiness_desc, dynamic_range_db }
│   ├── drums:  { duration, tempo_bpm, beat_regularity?, onsets_per_second,
│   │            kit_balance:{kick,snare,hihat} }
│   ├── bass:   { duration, dominant_notes:[str×4], root_movement_rate, root_movement_desc }
│   └── other:  { duration, centroid_hz, bandwidth_hz, texture, harmonic_pct, attack }
│
├── vocals: VocalAnalysis
│   ├── layers:        (vocal_layers) duration, layering, layering_pct?, harmonic_peaks_*,
│   │                  echo_detected, echo_count?, echoes?[{delay_s,strength}], dense_regions?[...]
│   ├── intervals:     (vocal_intervals) consonance_ratio, harmonic_character,
│   │                  interval_profile[13×{semitones,name,meaning,count,pct}], dominant_interval, sample_intervals[]
│   ├── narrative:     (vocal_narrative) total_phases, type_distribution{}, phases[], call_response_patterns[], segments[*]
│   ├── relationships: (vocal_relationships) relationship_distribution{}, story[], transitions[], moments[*],
│   │                  lead_pitch_center        # labels: silence|solo|support|dialogue|opposition|merge|withdraw
│   ├── register:      (register_tracking) singer_median_f0, singer_range_low/high (UNROUNDED), phases[], transitions[], moments[*]
│   └── breath:        (breath_detection) total_breaths, breaths_per_minute, depth_distribution{deep,normal,catch},
│                      context_distribution{}, breath_events[], phrase_durations[]
│
├── rhythm:
│   └── groove:        (groove_timing) tempo, beat_count, feel?, tightness?, swing_ratio?, drift?,
│                      timing_distribution{behind_pct,on_grid_pct,ahead_pct}, error?
│
├── harmony:
│   ├── chords:        (chord_progression) tempo, total_segments, unique_chords,
│   │                  segments[{chord,start,end,start_beat,end_beat,duration_beats,avg_confidence}],
│   │                  top_patterns[], modulations[], chord_sequence_summary[str]
│   ├── harmonic_rhythm: (harmonic_rhythm) avg/max/min_changes_per_bar, harmonic_arc, phases[],
│   │                  acceleration_events[], windows[]   # ⚠ degenerate branch emits "harmonic_rhythm_windows":[] instead
│   └── theory:        (music_theory) key, mode, key_confidence, cadences[], cadence_distribution{},
│                      unique_numerals[] (UNORDERED), analyzed_chords[{chord,start,end,analysis|null}]
│
├── timbre:
│   ├── decomposition: (timbral_decomposition) n_components, reconstruction_error, components[{...,instrument_guess,rank,energy_pct}]
│   └── interaction:   (freq_interaction) stem_count, pairs[], territory{}   # {} if <2 stems
│
├── spatial:
│   ├── stereo:        (stereo_field) EITHER {stereo:false, note} OR {stereo:true, mid_pct, side_pct,
│   │                  stereo_width, lr_balance, lr_correlation, band_width{}, width_timeline[], stereo_events?[]}
│   └── depth:         (depth_reverb) rt60_estimate, rt60_std?, pre_delay_ms, wetness_index,
│                      room_size, perceived_distance, spatial_placement, spectral_*
│
├── structure:        (temporal_segmentation) snapshots[{seg,t_center,time,rms_*,key,tension,consonance,warmth,...}],
│                     narrative{climax,quietest,peak_tension,transitions[],key_changes[],arc} | {}
│
├── emotion:          (emotional_trajectory) total_phases, total_transitions, unique_states,
│                     phases[{state,energy,start,end,avg_tension,avg_warmth,tension_trend?}],
│                     transitions[], trajectory_summary[], narrative:str   |  {error:str}
│
├── lyrics:           (semantic_lyrics — NOT PERSISTED TODAY) available:bool, source?, text?,
│                     vader{overall_sentiment,line_sentiments[]}, semantic{} (open/LLM), interpretation_gap?
│
├── story:            (story_reader) lyrics_source, total_lines, story_moments[{time,lyric,
│                     vocal_relationship,emotion,warmth,chord,vessel,alignment_confidence}]
│
├── ai_detection:     (ai_detector) overall_score, verdict, confidence, vectors_available/possible,
│                     vectors{} (sparse, ≤7), weights{}
│
└── genome: GenomeVector                       # the 12 floats below — see §3
```

**Optionality rule (the `ISSUE-008` fix):** every domain above is `| None`. A degraded/failed/missing
module yields `null` for its whole section — never a missing key, never an `{"error":...}` blob leaking
into a consumer. Consolidator validates once; downstream trusts the model.

---

## 3. The genome feature vector (DuckDB twin-search)

⚠ **This vector is computed in `genome_map.extract_feature_vector()` but never persisted** — only
aggregate stats are written. For DuckDB VSS we must **replicate that extraction** and store the raw
per-track vector. It is **12 dimensions**, sourced from `stem_analysis.json`:

| # | Dim | Source field |
|---|---|---|
| 1 | `vocal_pitch` | `vocals.pitch_mean_hz` |
| 2 | `vocal_range` | `vocals.pitch_range_semitones` |
| 3 | `vocal_entropy` | `vocals.vocal_melodic_entropy` |
| 4 | `vocal_breathiness` | `vocals.breathiness` |
| 5 | `vocal_presence` | `vocals.voiced_fraction` |
| 6 | `drum_tempo` | `drums.tempo_bpm` |
| 7 | `drum_regularity` | `drums.beat_regularity` |
| 8 | `drum_density` | `drums.onsets_per_second` |
| 9 | `drum_kick_pct` | `drums.kit_balance.kick` |
| 10 | `bass_movement` | `bass.root_movement_rate` |
| 11 | `texture_centroid` | `other.centroid_hz` |
| 12 | `texture_harmonic` | `other.harmonic_pct` |

### DuckDB schema

```sql
CREATE TABLE tracks (
  track_id         TEXT PRIMARY KEY,    -- stem folder name (the universal join key)
  title            TEXT,
  artist           TEXT,
  source_path      TEXT,
  duration_s       DOUBLE,
  key              TEXT,                -- music_theory.key
  mode             TEXT,                -- music_theory.mode
  tempo            DOUBLE,              -- chord_progression.tempo
  valence          DOUBLE,              -- emotion summary (derive)
  arousal          DOUBLE,              -- emotion summary (derive)
  ai_verdict       TEXT,                -- ai_detector.verdict
  ai_score         DOUBLE,              -- ai_detector.overall_score
  pipeline_version TEXT,
  analyzed_at      TIMESTAMP,
  perception_path  TEXT                 -- pointer to the full PerceptionDocument JSON
);

CREATE TABLE genome_vectors (
  track_id  TEXT PRIMARY KEY,
  vector    FLOAT[12]                   -- the 12 dims above
);
-- HNSW/VSS index on genome_vectors.vector for nearest-neighbour twin lookup
```

`tracks` upserted by `track_id` — idempotent, no dup rows on re-analysis.

---

## 4. Library- & pair-level artifacts (NOT in PerceptionDocument)

- **`genome_map.json`** — cross-track: `genome{}` per-feature stats, `most_similar_pairs[]`,
  `neighbors{}`, `most_typical_track`, `distances_from_center{}`. The per-track vector itself is *not*
  here (see §3). → In the app, this is **derived from DuckDB**, not a stored file.
- **`temporal_genome.json`** — `tracks[]` (year-sorted), `eras{}`, `genre_clusters{}`. ⚠ Driven by a
  **hardcoded `METADATA` dict** (track→year/artist/genre/era) that only knows Barry's specific library;
  unknown tracks get `year:0,"Unknown"`. Must become real per-track metadata (DB columns), not code.
- **`version_compare.json`** — pair-level producer-fingerprint deltas; sparse `deltas{}` blocks +
  `fingerprint_top_changes[]`. Stays a standalone tool/view, not part of the per-track doc.

---

## 5. Schema hazards (consolidator requirements)

| Hazard | Where | Requirement |
|---|---|---|
| **NaN → invalid JSON** | `stereo_field.lr_correlation`, `music_theory.key_confidence`, `temporal_segmentation.arc.*_thirds` | Sanitize non-finite floats to `null` at the boundary (also `ISSUE-004`) |
| **int-vs-float "0" fallbacks** | analyze_stems, vocal_intervals, breath_detection, freq_interaction, depth_reverb | Schema types these `float`; coerce on ingest |
| **Variant array shapes** | `segments`/`moments` in vocal_narrative/relationships/register (silence variants drop keys) | Model the union; missing per-frame keys → `None` |
| **Key-name split** | harmonic_rhythm: `windows` vs `harmonic_rhythm_windows` (degenerate branch) | Normalize to one field name |
| **Two root shapes** | stereo (mono vs stereo), emotion (`{error}` vs full), groove (3 shapes), breath (empty vs full) | Branch on discriminator; never index blindly |
| **Nullable nested** | `music_theory.analyzed_chords[].analysis` can be `null` | Already nullable — preserve |
| **Filename-replace fragility** | emotional_trajectory / harmonic_rhythm / music_theory derive output via `.replace("_chords.json",...)` | Refactor: pass explicit output paths (dies with the in-process refactor) |
| **Nondeterministic order** | `music_theory.unique_numerals = list(set(...))` | Sort for stable output |

---

## 6. Build-relevant findings (new — surfaced during mapping)

1. **`semantic_lyrics` is never persisted** — it prints to stdout only. The orchestrator runs it but
   captures nothing, so the VADER + LLM lyric analysis is **computed and thrown away** in pipeline
   context. The consolidator must capture its return value (in-process refactor makes this natural).
2. **The LLM lives in `semantic_lyrics`, not `story_reader`.** `story_reader` is **rule-based** narrative
   synthesis — it does *not* call an LLM, despite CLAUDE.md/README describing the "grounded story reading"
   as LLM-fed. The actual Claude API call (`claude-sonnet-4-20250514`) is in `semantic_lyrics`. Docs and
   architecture need to reconcile which module owns the grounded-LLM reading.
3. **`temporal_genome.METADATA` is hardcoded** to Barry's tracks — a general tool can't ship this. Track
   era/year/artist/genre must become real metadata (DB columns / file tags), not a code dict.
4. **The genome vector must be persisted** (§3) — today it evaporates after `genome_map` runs.
5. **`ai_detector --batch` emits a JSON array**, single mode emits an object — different root types.

Items 1–3 are genuine debt/architecture issues worth filing; 4–5 are consolidator/build design notes.
