-- supervisor-agent fused portfolio database — CUMULATIVE DDL, versioned as code.
-- Implements BUILD-SPEC.md §3.1. Every statement is idempotent (IF NOT EXISTS) so
-- the full script replays safely on any database, alongside the numbered migrations
-- in db/migrations/ (see BUILD-SPEC §3.5 build-time rule below the file inventory).
--
-- Phase status of this snapshot: phase 0 (meta / provenance / runs / decision_log only).
-- Later phases extend this file with their tables (§3.1 core fused state,
-- staleness/implication/ranking, TTP layer, human outputs) and add the matching
-- numbered migration.

PRAGMA journal_mode = WAL;

-- ─── meta / provenance backbone ──────────────────────────────────────────────
-- Every substantive row that asserts a PORTFOLIO fact carries provenance_id
-- (non-nullable). Self-governance tables (meta, runs, decision_log, and later
-- audit_runs) are the exception by construction: each row's provenance IS the
-- run that wrote it, so the §7 provenance-null check scopes to tables that
-- actually have a provenance_id column.

CREATE TABLE IF NOT EXISTS provenance (
    id           INTEGER PRIMARY KEY,
    source_ref   TEXT NOT NULL,   -- file path + anchor (file.md#heading or file:line)
    source_sha   TEXT,            -- blob hash when the source is committed content
    source_type  TEXT NOT NULL,   -- registry id from ontology/sources.yaml
    derived_from BLOB,            -- JSON: which upstream rows/queries produced this
    note         TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id               INTEGER PRIMARY KEY,
    started_at       TEXT,
    ended_at         TEXT,
    trigger          TEXT,
    sources_parsed   TEXT,   -- JSON list of registry ids parsed this run
    degraded_sources TEXT,   -- JSON list of registry ids degraded to authority 0
    db_version       INTEGER,
    schema_hash      TEXT,
    outcome          TEXT
);

CREATE TABLE IF NOT EXISTS decision_log (
    id        INTEGER PRIMARY KEY,
    at        TEXT NOT NULL,
    kind      TEXT NOT NULL,
    brief_id  INTEGER NULL,
    ticket_id INTEGER NULL,
    outcome   TEXT NOT NULL,
    detail    TEXT NOT NULL
);


-- ────────────────────────────────────────────────────────────────────────
-- phase 1 (cumulative snapshot continuation — matches migration 0002)


CREATE TABLE IF NOT EXISTS parse_failures (
    id            INTEGER PRIMARY KEY,
    source_ref    TEXT NOT NULL,
    at            TEXT NOT NULL,
    detail        TEXT NOT NULL,
    provenance_id INTEGER NOT NULL REFERENCES provenance(id)
);

CREATE TABLE IF NOT EXISTS initiatives (
    id              INTEGER PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN (
        'project1_fuzz', 'project2_mutation', 'project3_drift',
        'vulnres_suite', 'supervisor', 'vm_sec_research')),
    status          TEXT NOT NULL,
    phase_coverage  TEXT,
    owner_gate      TEXT,
    proposal_ref    TEXT,
    status_file_ref TEXT NULL,          -- NULL until a project's phase-1 file exists
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id             INTEGER PRIMARY KEY,
    initiative_id  INTEGER NOT NULL REFERENCES initiatives(id),
    kind           TEXT NOT NULL CHECK (kind IN (
        'knowledge', 'sweep_summary', 'finding', 'exploit', 'milestone',
        'measurement', 'rollup', 'environment_entry', 'fuzz_result', 'commit_event')),
    verdict_class  TEXT,
    content_hash   TEXT,
    asserted_at    TEXT NULL,   -- the updated:/sweep date the claim itself asserts
    source_ref     TEXT NOT NULL,
    provenance_id  INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at    TEXT NOT NULL,
    UNIQUE(source_ref, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_evidence_initiative ON evidence(initiative_id);
CREATE INDEX IF NOT EXISTS idx_evidence_kind ON evidence(kind);

CREATE TABLE IF NOT EXISTS milestones (
    id             INTEGER PRIMARY KEY,
    initiative_id  INTEGER NOT NULL REFERENCES initiatives(id),
    m_ref          TEXT NOT NULL,               -- 'M8' …
    title          TEXT NOT NULL,               -- verbatim from the table row
    status         TEXT NOT NULL,               -- verbatim from the table row
    evidence_ref   TEXT,
    provenance_id  INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at    TEXT NOT NULL,
    UNIQUE(initiative_id, m_ref)                -- invariant: never renumbered/inserted
);
CREATE INDEX IF NOT EXISTS idx_milestones_initiative ON milestones(initiative_id);
CREATE INDEX IF NOT EXISTS idx_milestones_ref ON milestones(m_ref);

CREATE TABLE IF NOT EXISTS milestone_log (
    id              INTEGER PRIMARY KEY,
    initiative_id   INTEGER NOT NULL REFERENCES initiatives(id),
    occurred_at     TEXT NOT NULL,              -- the dated entries BEHIND the table;
    sequence        INTEGER NOT NULL,           -- source order, 1-based within file
    heading         TEXT NOT NULL,              -- verbatim heading after '--'
    m_refs_touched  TEXT,                       -- JSON list of 'M8'-style refs
    detail          TEXT NOT NULL,
    next_up         TEXT,                       -- 'Next up' lines: decision-engine input
    entry_key       TEXT NOT NULL UNIQUE,
    provenance_id   INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mlog_initiative ON milestone_log(initiative_id);

CREATE TABLE IF NOT EXISTS links (
    id            INTEGER PRIMARY KEY,
    src_type      TEXT NOT NULL,
    src_id        INTEGER NOT NULL,
    dst_type      TEXT NOT NULL,
    dst_id        INTEGER NOT NULL,
    link_type     TEXT NOT NULL,
    weight        REAL DEFAULT 1.0,
    provenance_id INTEGER NOT NULL REFERENCES provenance(id),
    ingested_at   TEXT NOT NULL,
    UNIQUE(src_type, src_id, dst_type, dst_id, link_type)
);
CREATE INDEX IF NOT EXISTS idx_links_src ON links(src_type, src_id);
CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst_type, dst_id);


-- ────────────────────────────────────────────────────────────────────────
-- phase 2 (cumulative snapshot continuation — matches migration 0003)
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

-- phase 1 note: migration 0002 (parse_failures, initiatives, evidence,
-- milestones, milestone_log, links) stands between the phase-0 block and
-- this block in the migration history; see that file for its DDL.
