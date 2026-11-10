-- Migration 0003 — phase 2: full fusion (sources 3–7), staleness clocks,
-- file-level implication, and the honestly-empty project-artifact tables the
-- §3.4 accounting map names (fuzz_targets, fleet_enrollments, schedules,
-- cadence_reports) so the accounting query can tick them at zero rows from day
-- one rather than pretend those families don't exist.
-- Idempotent by construction. Schema-shape build-time amendment: findings and
-- exploits carry their verbatim index text as data (score ranges, statuses are
-- prose in this suite's indices — parsing them out into integers would be
-- crossing from parsed data into judgment).

-- ─── the vuln_res suite, first-class ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sweeps (
    id              INTEGER PRIMARY KEY,
    initiative_id   INTEGER NOT NULL REFERENCES initiatives(id),
    sweep_id        TEXT NOT NULL UNIQUE,          -- '2026-11-10-001-recon-verification'
    kind            TEXT NOT NULL CHECK (kind IN (
        'recon', 'fuzz_harness', 'environment_run', 'triage', 'exploit_dev',
        'disclosure', 'full_orchestrated')),
    report_dir      TEXT NOT NULL,
    started_at      TEXT,
    closed_at       TEXT,
    outcome         TEXT,                          -- verbatim summary lines
    agents_invoked  TEXT,                          -- JSON list; proves orchestrator shape
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY,
    sweep_id        INTEGER REFERENCES sweeps(id),    -- NULL until its sweep parsed
    sweep_label     TEXT NOT NULL,                    -- registry id, resolves post-load
    finding_ref     TEXT NOT NULL UNIQUE,             -- slug/source path
    title           TEXT NOT NULL,
    score           TEXT,                             -- verbatim, e.g. '9 (3×1×3)'
    disposition     TEXT NOT NULL,                    -- verbatim status column
    resolution_ref  TEXT,                             -- fix commit / test refs when stated
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_sweep ON findings(sweep_id);

CREATE TABLE IF NOT EXISTS exploits (
    id              INTEGER PRIMARY KEY,
    finding_id      INTEGER REFERENCES findings(id),
    outcome_class   TEXT CHECK (outcome_class IN ('our_code', 'upstream', 'escalate')),
    artifact_ref    TEXT,
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS environments (
    id              INTEGER PRIMARY KEY,
    env_id          TEXT NOT NULL UNIQUE,          -- registry kebab-case id
    provider        TEXT,                          -- tart | docker | orbstack | remote-… | other
    lifecycle       TEXT,                          -- disposable | persistent
    status          TEXT,                          -- active | torn-down
    created_at      TEXT,
    created_by      TEXT,
    approved_for    TEXT,                          -- JSON list, scoped (registry rule 2)
    approved_by     TEXT,
    network         TEXT,                          -- isolated | host-bridged | unknown
    resource_caps   TEXT,                          -- JSON, registry SCHEMA.md fields verbatim
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capabilities (
    id               INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    agent_or_skill   TEXT NOT NULL UNIQUE,         -- repo path of the definition
    kind             TEXT NOT NULL CHECK (kind IN
                     ('agent', 'skill', 'project_runner', 'supervisor')),
    suite            INTEGER NOT NULL REFERENCES initiatives(id),
    approval_class   TEXT NOT NULL CHECK (approval_class IN
                     ('autonomous', 'user_gated', 'gated_plus_1tr')),
    trigger_contract TEXT NOT NULL,                -- the file's own description, verbatim
    provenance_id    INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cadence_reports (
    id              INTEGER PRIMARY KEY,
    initiative_id   INTEGER NOT NULL REFERENCES initiatives(id),
    cadence         TEXT NOT NULL CHECK (cadence IN ('daily', 'weekly', 'monthly')),
    path            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cadence_reports ON cadence_reports(cadence, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS cadence_reports_path ON cadence_reports(path, created_at);

CREATE TABLE IF NOT EXISTS fuzz_targets (
    id              INTEGER PRIMARY KEY,
    initiative_id   INTEGER NOT NULL REFERENCES initiatives(id),
    name            TEXT,
    target_path     TEXT,
    harness_ref     TEXT,
    seed_corpus_ref TEXT,
    last_run_at     TEXT,                          -- NULL = first-class 'never fuzzed'
    last_result     TEXT,
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fleet_enrollments (
    id              INTEGER PRIMARY KEY,
    initiative_id   INTEGER NOT NULL REFERENCES initiatives(id),
    hostname        TEXT NOT NULL UNIQUE,
    enrolled_at     TEXT,
    enrolled_by     TEXT NOT NULL CHECK (enrolled_by = 'user'),
    baseline_ref    TEXT,
    last_eval_at    TEXT,
    last_eval_state TEXT,
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id               INTEGER PRIMARY KEY,
    capability_id    INTEGER REFERENCES capabilities(id),
    cadence          TEXT,
    approval_status  TEXT NOT NULL CHECK (approval_status IN ('proposed', 'approved', 'retired')),
    approved_by      TEXT NULL,                    -- row-changed by user only (§3.1)
    approved_at      TEXT NULL,
    provenance_id    INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at      TEXT NOT NULL
);

-- ─── staleness / implication ─────────────────────────────────────────────────

-- The date a knowledge/climate claim itself asserts (`updated:` / sweep date),
-- kept out of evidence on purpose: it is parsed data about the CLAIM's
-- chronology, and R2's join needs it as a first-class column.
CREATE TABLE IF NOT EXISTS claim_anchors (
    evidence_id INTEGER PRIMARY KEY REFERENCES evidence(id),
    asserted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staleness_clocks (
    id                INTEGER PRIMARY KEY,
    capability_id     INTEGER REFERENCES capabilities(id),
    initiative_id     INTEGER REFERENCES initiatives(id),
    surface           TEXT NOT NULL UNIQUE,
    last_verified_at  TEXT NULL,                   -- NULL = 'never', first-class
    last_verified_by  INTEGER REFERENCES evidence(id),
    invalidates_on    TEXT NOT NULL,               -- JSON list of path prefixes / producers
    policy            TEXT NOT NULL,
    state             TEXT NOT NULL CHECK (state IN
                      ('live', 'invalid', 'never', 'missing_evidence')),
    provenance_id     INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_clocks_state ON staleness_clocks(state);
CREATE INDEX IF NOT EXISTS idx_clocks_surface ON staleness_clocks(surface);

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('commit', 'synthetic', 'file_change')),
    occurred_at   TEXT NOT NULL,
    ref           TEXT,                            -- git sha / described origin
    paths         TEXT NOT NULL,                   -- JSON array of touched paths
    detail        TEXT NOT NULL,
    provenance_id INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at   TEXT NOT NULL,
    UNIQUE(kind, ref)
);
CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at);

CREATE TABLE IF NOT EXISTS clock_invalidation_events (
    clock_id INTEGER NOT NULL REFERENCES staleness_clocks(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    fired_at TEXT NOT NULL,
    UNIQUE(clock_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_cie_clock ON clock_invalidation_events(clock_id);

CREATE TABLE IF NOT EXISTS contradictions (
    id                 INTEGER PRIMARY KEY,
    losing_evidence_id INTEGER NOT NULL REFERENCES evidence(id),
    winning_evidence_id INTEGER NOT NULL REFERENCES evidence(id),
    rule_id            TEXT NOT NULL,             -- reviewed rule in db/queries/
    detected_at        TEXT NOT NULL,
    detail             TEXT NOT NULL,
    provenance_id      INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at        TEXT NOT NULL,
    UNIQUE(losing_evidence_id, winning_evidence_id, rule_id)
);
