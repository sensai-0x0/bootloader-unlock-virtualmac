-- Migration 0007 — phase 5: TTP layer (pin, map, profile, simulate).
-- BUILD-SPEC §3.1 "TTP layer (Phase 5)", §3.3's requirement→schema map, §5.

-- ─── releases: re-pinning is inserting a row, never updating in place (A6) ──
CREATE TABLE IF NOT EXISTS attack_releases (
    id          INTEGER PRIMARY KEY,
    tag         TEXT UNIQUE NOT NULL,       -- 'ATT&CK-v20.1'
    released_at TEXT,
    bundle_url  TEXT NOT NULL,
    bundle_sha256 TEXT UNIQUE NOT NULL,
    is_pinned   INTEGER NOT NULL DEFAULT 0,
    ingested_at TEXT NOT NULL
);
-- at most one pinned release: enforced by the ingest path (ingest.py), not a
-- CHECK (SQLite CHECK can't reference other rows); re-verified by self-audit.

CREATE TABLE IF NOT EXISTS tactics (
    id          INTEGER PRIMARY KEY,
    attack_id   TEXT UNIQUE NOT NULL,       -- 'TA0007'
    name        TEXT NOT NULL,
    short_name  TEXT NOT NULL               -- drives phase_tactics joins
);

CREATE TABLE IF NOT EXISTS techniques (
    id               INTEGER PRIMARY KEY,
    attack_id        TEXT UNIQUE NOT NULL,  -- 'T1608', 'T1608.007'
    name             TEXT NOT NULL,
    is_subtechnique  INTEGER NOT NULL DEFAULT 0,
    parent_attack_id TEXT,                  -- self-join for base rollup (A3)
    description      TEXT,
    revoked          INTEGER NOT NULL DEFAULT 0,
    deprecated       INTEGER NOT NULL DEFAULT 0,
    release_id       INTEGER NOT NULL REFERENCES attack_releases(id)
);
CREATE INDEX IF NOT EXISTS idx_tech_parent ON techniques(parent_attack_id);

-- version history per technique: diffing v20.1 -> v21 = comparing rows (A6)
CREATE TABLE IF NOT EXISTS technique_revisions (
    id                  INTEGER PRIMARY KEY,
    technique_attack_id TEXT NOT NULL,
    release_id          INTEGER NOT NULL REFERENCES attack_releases(id),
    version             TEXT NOT NULL,
    revision_note       TEXT,
    UNIQUE(technique_attack_id, release_id)
);

-- multi-valued facets: a technique maps to SEVERAL tactics and platforms (A1, A5)
CREATE TABLE IF NOT EXISTS technique_tactics (
    technique_id INTEGER NOT NULL REFERENCES techniques(id),
    tactic_id    INTEGER NOT NULL REFERENCES tactics(id),
    UNIQUE(technique_id, tactic_id)
);
CREATE INDEX IF NOT EXISTS idx_tt_tactic ON technique_tactics(tactic_id);

CREATE TABLE IF NOT EXISTS technique_platforms (
    technique_id INTEGER NOT NULL REFERENCES techniques(id),
    platform     TEXT NOT NULL,
    UNIQUE(technique_id, platform)
);

CREATE TABLE IF NOT EXISTS technique_groups (
    technique_id    INTEGER NOT NULL REFERENCES techniques(id),
    group_attack_id TEXT NOT NULL,
    group_name      TEXT NOT NULL,
    source_ref      TEXT NOT NULL,          -- STIX relationship id, in-release
    UNIQUE(technique_id, group_attack_id, source_ref)
);
CREATE INDEX IF NOT EXISTS idx_tg_group ON technique_groups(group_attack_id);

CREATE TABLE IF NOT EXISTS technique_campaigns (
    technique_id       INTEGER NOT NULL REFERENCES techniques(id),
    campaign_attack_id TEXT NOT NULL,
    campaign_name      TEXT NOT NULL,
    source_ref         TEXT NOT NULL,
    UNIQUE(technique_id, campaign_attack_id)
);

CREATE TABLE IF NOT EXISTS technique_detcount (
    technique_id    INTEGER NOT NULL REFERENCES techniques(id),
    release_id      INTEGER NOT NULL REFERENCES attack_releases(id),
    det_strategies  INTEGER NOT NULL DEFAULT 0,
    analytics       INTEGER NOT NULL DEFAULT 0,
    UNIQUE(technique_id, release_id)
);

-- ─── mapping of techniques to THIS portfolio's check surfaces ──────────────
-- the analytics heart: a 'covered' verdict with NULL evidence_id is
-- structurally impossible — enforced at ingest, not just by convention
-- (BUILD-SPEC §3.3 item 2 / §5.5's self-check turned into schema).
CREATE TABLE IF NOT EXISTS ttp_mappings (
    id             INTEGER PRIMARY KEY,
    technique_id   INTEGER NOT NULL REFERENCES techniques(id),
    surface        TEXT NOT NULL,           -- e.g. 'cargo-audit-clean', 'enrolled-fleet-ssh'
    capability_id  INTEGER REFERENCES capabilities(id),
    detect_via     TEXT,
    limit_via      TEXT,
    verdict        TEXT NOT NULL CHECK (verdict IN
                   ('covered', 'partially_covered', 'uncovered',
                    'asserted_unproven', 'not_applicable')),
    evidence_id    INTEGER REFERENCES evidence(id),
    provenance_id  INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at    TEXT NOT NULL,
    UNIQUE(technique_id, surface),
    CHECK (verdict != 'covered' OR evidence_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_map_capability ON ttp_mappings(capability_id);
CREATE INDEX IF NOT EXISTS idx_map_technique ON ttp_mappings(technique_id);

-- portfolio phases: which tactics belong to which standing-program phase (A1)
-- REVIEWED DATA (not code): init/recon <- Reconnaissance, Resource Development;
-- persist/expand <- Persistence, Privilege Escalation, Defense Evasion,
-- Discovery, Lateral Movement; execute <- Initial Access, Execution;
-- triage-learn <- Collection, Credential Access, Exfiltration;
-- persist/report <- Command and Control, Impact.
CREATE TABLE IF NOT EXISTS phase_tactics (
    id               INTEGER PRIMARY KEY,
    phase            TEXT NOT NULL,
    tactic_attack_id TEXT NOT NULL REFERENCES tactics(attack_id),
    UNIQUE(phase, tactic_attack_id)
);

-- ─── adversary profiles and the simulated decision loop (A4) ───────────────
CREATE TABLE IF NOT EXISTS tp_profiles (
    id            INTEGER PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,
    description   TEXT NOT NULL,
    skill_level   TEXT NOT NULL,
    patience      TEXT NOT NULL,
    phase_vector  TEXT NOT NULL,            -- JSON ordered list of phases
    notes         TEXT,
    provenance_id INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sim_scenarios (
    id             INTEGER PRIMARY KEY,
    profile_id     INTEGER NOT NULL REFERENCES tp_profiles(id),
    seed           INTEGER NOT NULL,
    phase_sequence TEXT NOT NULL,           -- JSON list, seeded from phase_vector
    release_id     INTEGER NOT NULL REFERENCES attack_releases(id),
    created_at     TEXT NOT NULL,
    run_id         INTEGER REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS sim_steps (
    id                 INTEGER PRIMARY KEY,
    scenario_id        INTEGER NOT NULL REFERENCES sim_scenarios(id),
    seq                INTEGER NOT NULL,
    technique_id       INTEGER NOT NULL REFERENCES techniques(id),
    intent             TEXT NOT NULL,
    success_predicted  INTEGER NOT NULL,    -- 0/1: would this step's premise hold
    basis              TEXT NOT NULL,       -- provenance text; 'deterred: <reason>' is first-class
    UNIQUE(scenario_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_sim_steps_scenario ON sim_steps(scenario_id);

CREATE TABLE IF NOT EXISTS sim_gaps (
    id                 INTEGER PRIMARY KEY,
    scenario_id        INTEGER NOT NULL REFERENCES sim_scenarios(id),
    step_id            INTEGER NOT NULL REFERENCES sim_steps(id),
    gap_kind           TEXT NOT NULL,
    question           TEXT NOT NULL,
    verdict            TEXT NOT NULL,
    raised_into_brief  INTEGER NOT NULL DEFAULT 0,
    recommendation_id  INTEGER REFERENCES recommendations(id)
);
CREATE INDEX IF NOT EXISTS idx_sim_gaps_scenario ON sim_gaps(scenario_id);

CREATE TABLE IF NOT EXISTS sim_outcomes (
    id                 INTEGER PRIMARY KEY,
    scenario_id        INTEGER UNIQUE NOT NULL REFERENCES sim_scenarios(id),
    summary            TEXT NOT NULL,
    top_gap_ids        TEXT NOT NULL,       -- JSON list
    coverage_by_phase  TEXT NOT NULL        -- JSON object
);

-- ─── views (§3.3's requirement -> schema map) ───────────────────────────────

-- A1: phase becomes data, reviewable in diffs, never hardcoded in rendering.
CREATE VIEW IF NOT EXISTS v_technique_phase AS
SELECT t.*, pt.phase
FROM techniques t
JOIN technique_tactics tt ON tt.technique_id = t.id
JOIN tactics ta ON ta.id = tt.tactic_id
JOIN phase_tactics pt ON pt.tactic_attack_id = ta.attack_id;

-- A3: coverage of a sub-technique implies base-level coverage; this view
-- rolls sub-technique mapping rows up to their base technique so brief
-- counts never double-count a mapped sub-technique against its base.
CREATE VIEW IF NOT EXISTS v_coverage_rollup AS
SELECT
    COALESCE(base.id, t.id)               AS base_technique_id,
    COALESCE(base.attack_id, t.attack_id) AS base_attack_id,
    m.verdict,
    m.surface,
    m.evidence_id,
    m.technique_id                        AS mapped_technique_id
FROM ttp_mappings m
JOIN techniques t ON t.id = m.technique_id
LEFT JOIN techniques base ON base.attack_id = t.parent_attack_id;

-- A6: re-pin diff — new/revoked/major-changed techniques intersecting
-- already-mapped surfaces, surfaced as a needs-human brief item, never a
-- silent content refresh. Compares the two most recent attack_releases rows.
CREATE VIEW IF NOT EXISTS v_repin_diff AS
WITH releases_ranked AS (
    SELECT id, tag, released_at,
           row_number() OVER (ORDER BY released_at DESC) AS rn
    FROM attack_releases
),
prev AS (SELECT id FROM releases_ranked WHERE rn = 2),
curr AS (SELECT id FROM releases_ranked WHERE rn = 1)
SELECT
    cur_t.attack_id,
    cur_t.name,
    CASE
        WHEN prev_t.id IS NULL THEN 'new'
        WHEN cur_t.revoked = 1 AND prev_t.revoked = 0 THEN 'revoked'
        ELSE 'changed'
    END AS change_kind,
    EXISTS (SELECT 1 FROM ttp_mappings m WHERE m.technique_id = prev_t.id) AS was_mapped
FROM curr, techniques cur_t
LEFT JOIN techniques prev_t
    ON prev_t.attack_id = cur_t.attack_id AND prev_t.release_id = (SELECT id FROM prev)
WHERE cur_t.release_id = (SELECT id FROM curr)
  AND (prev_t.id IS NULL
       OR cur_t.revoked != prev_t.revoked
       OR cur_t.deprecated != prev_t.deprecated);
