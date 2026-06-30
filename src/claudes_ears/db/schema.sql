-- DuckDB library index (frozen DDL): a rebuildable cache over per-track JSONs.
-- library.py upserts `tracks` by track_id; the VSS index lives in twins.py.

CREATE TABLE IF NOT EXISTS tracks (
  track_id         TEXT PRIMARY KEY,    -- stem-folder name (the universal join key)
  title            TEXT,
  artist           TEXT,
  -- Per-track metadata (ISSUE-014 / decision 1.4.2) — real columns, not a code dict.
  -- Fed to temporal_genome.analyze(metadata=...) for era/genre clustering.
  year             INTEGER,
  genre            TEXT,
  era              TEXT,
  source_path      TEXT,
  duration_s       DOUBLE,
  key              TEXT,                -- music_theory.key
  mode             TEXT,                -- music_theory.mode
  tempo            DOUBLE,              -- chord_progression.tempo
  valence          DOUBLE,              -- emotion summary (derived)
  arousal          DOUBLE,              -- emotion summary (derived)
  ai_verdict       TEXT,                -- ai_detector.verdict
  ai_score         DOUBLE,              -- ai_detector.overall_score
  pipeline_version TEXT,
  analyzed_at      TIMESTAMP,
  perception_path  TEXT                 -- pointer to the full PerceptionDocument JSON
);

-- The 12-dim genome feature vector per track (schema.md §3). FLOAT[12] is the
-- fixed-width VSS contract; the dimension order is GenomeVector.DIMS.
CREATE TABLE IF NOT EXISTS genome_vectors (
  track_id  TEXT PRIMARY KEY,
  vector    FLOAT[12]
);

-- HNSW/VSS index — created and refreshed by db/twins.py after `LOAD vss`:
--   SET hnsw_enable_experimental_persistence = true;
--   CREATE INDEX IF NOT EXISTS genome_hnsw ON genome_vectors USING HNSW (vector);
