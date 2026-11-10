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

CREATE TABLE IF NOT EXISTS audit_runs (
    id                 INTEGER PRIMARY KEY,
    run_id             INTEGER NULL REFERENCES runs(id),
    checklist_version  TEXT NOT NULL,
    passed             INTEGER NOT NULL,
    violations         TEXT NOT NULL,   -- JSON list; empty list = clean pass
    at                 TEXT NOT NULL
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


-- ────────────────────────────────────────────────────────────────────────
-- phase 3 (cumulative snapshot continuation — matches migration 0005)
-- Snapshot-first means snapshot-complete (§3.5 item 10): this block is a
-- verbatim copy of migration 0005's DDL so a fresh database built from this
-- file alone (no ledger replay) still has score_runs/recommendations/
-- implications and the v_phase_coverage/v_score_inputs views.

CREATE TABLE IF NOT EXISTS score_runs (
    id          INTEGER PRIMARY KEY,
    computed_at TEXT NOT NULL,
    inputs_hash TEXT NOT NULL UNIQUE   -- sha256 over canonical (sorted) v_score_inputs rows
);

CREATE TABLE IF NOT EXISTS recommendations (
    id                   INTEGER PRIMARY KEY,
    score_run_id         INTEGER NOT NULL REFERENCES score_runs(id),
    rank                 INTEGER NOT NULL,
    initiative_id        INTEGER NULL REFERENCES initiatives(id),
    capability_id        INTEGER NULL REFERENCES capabilities(id),
    score_total          REAL NOT NULL,
    score_staleness      REAL NOT NULL,
    score_blast          REAL NOT NULL,
    score_readiness      REAL NOT NULL,
    score_precedent      REAL NOT NULL,
    required_gate        TEXT NOT NULL,
    brief_id             INTEGER NULL,  -- FK deferred to phase 4; briefs do not exist yet
    component_provenance TEXT NOT NULL, -- JSON list: every component names its input rows
    UNIQUE(score_run_id, rank)
);
CREATE INDEX IF NOT EXISTS idx_recommendations_run ON recommendations(score_run_id);

CREATE TABLE IF NOT EXISTS implications (
    id            INTEGER PRIMARY KEY,
    event_id      INTEGER NOT NULL REFERENCES events(id),
    effect_kind   TEXT NOT NULL,        -- e.g. 'clock_invalidated'
    effect_ref    TEXT NOT NULL,        -- e.g. the clock surface
    rule_id       TEXT NOT NULL,        -- the reviewed rule that fired (R1 v2 today)
    provenance_id INTEGER NOT NULL REFERENCES provenance(id),
    UNIQUE(event_id, effect_kind, effect_ref, rule_id)
);
CREATE INDEX IF NOT EXISTS idx_implications_event ON implications(event_id);

CREATE VIEW IF NOT EXISTS v_phase_coverage AS
SELECT
    i.id                                         AS initiative_id,
    i.slug                                       AS slug,
    ph.phase                                     AS phase,
    CASE i.kind || '|' || ph.phase
      WHEN 'vulnres_suite|recon'        THEN 'green'
      WHEN 'vulnres_suite|build'        THEN
        CASE WHEN EXISTS (SELECT 1 FROM staleness_clocks sc
                          WHERE sc.initiative_id = i.id AND sc.state = 'live')
             THEN 'green' ELSE 'stale' END
      WHEN 'vulnres_suite|execute'      THEN 'blocked'
      WHEN 'vulnres_suite|triage-learn' THEN 'green'
      WHEN 'vulnres_suite|persist-report' THEN 'green'
      WHEN 'vm_sec_research|recon'      THEN 'green'
      WHEN 'vm_sec_research|build'      THEN 'green'
      WHEN 'vm_sec_research|execute'    THEN 'green'
      WHEN 'vm_sec_research|triage-learn' THEN 'green'
      WHEN 'vm_sec_research|persist-report' THEN 'green'
      WHEN 'supervisor|recon'           THEN 'green'
      WHEN 'supervisor|build'           THEN 'in-progress'
      WHEN 'supervisor|execute'         THEN 'never-run'
      WHEN 'supervisor|triage-learn'    THEN
        CASE WHEN EXISTS (SELECT 1 FROM recommendations LIMIT 1) THEN 'in-progress'
             ELSE 'never-run' END
      WHEN 'supervisor|persist-report'  THEN
        CASE WHEN EXISTS (SELECT 1 FROM decision_log
                          WHERE kind = 'phase-verification') THEN 'in-progress'
             ELSE 'never-run' END
      ELSE
        CASE WHEN ph.phase IN ('execute') THEN 'blocked' ELSE 'never-run' END
    END AS state,
    CASE i.kind || '|' || ph.phase
      WHEN 'vulnres_suite|recon'
        THEN 'sweeps parsed: ' ||
             (SELECT count(*) FROM sweeps) || ' recon sweeps, latest ' ||
             (SELECT max(started_at) FROM sweeps) || ' [source: sweeps table]'
      WHEN 'vulnres_suite|build'
        THEN 'clean-as-of knowledge claims are contradictions R2 rows 1–6 (sweep 2026-11-11-001 postdate); clocks knowledge:* [source: staleness_clocks + contradictions]'
      WHEN 'vulnres_suite|execute'
        THEN 'environments rows = ' || (SELECT count(*) FROM environments) ||
             ' → execute phase structurally blocked; §4.2 state fact [source: environments registry (empty)]'
      WHEN 'vulnres_suite|triage-learn'
        THEN 'findings parsed: ' || (SELECT count(*) FROM findings) ||
             ' with dispositions [source: findings table + sweep-reports/findings-index.md]'
      WHEN 'vulnres_suite|persist-report'
        THEN 'knowledge INDEX + cross-sweep INDEX parsed (' ||
             (SELECT count(*) FROM evidence WHERE initiative_id = i.id) ||
             ' evidence rows); cadence rollups = ' ||
             (SELECT count(*) FROM cadence_reports) ||
             ' → cadence never-run [source: evidence, cadence_reports]'
      WHEN 'vm_sec_research|recon'
        THEN 'M0–M2 done (plan, IPSW ground-truth extraction, M6 fixtures) [source: milestones M0/M1/M2]'
      WHEN 'vm_sec_research|build'
        THEN 'M8 VM path realized: VM booted per milestone log 2026-11-10 [source: milestone_log + M8/M9/M10]'
      WHEN 'vm_sec_research|execute'
        THEN 'M9 + M10: bputil mutation path proven inside the VM, full round trip evidenced [source: milestones M9/M10 status Done]'
      WHEN 'vm_sec_research|triage-learn'
        THEN 'M7 decision recorded: VM path over scratch hardware [source: milestones M7 + milestone_log]'
      WHEN 'vm_sec_research|persist-report'
        THEN 'milestone_log dated entries: ' ||
             (SELECT count(*) FROM milestone_log) ||
             ' [source: progress/milestones.md log section]'
      WHEN 'supervisor|recon'
        THEN 'sources 1–7 parsed, evidence rows = ' ||
             (SELECT count(*) FROM evidence) || ' [source: parse_runs + evidence]'
      WHEN 'supervisor|build'
        THEN 'phases 0–' ||
             (SELECT count(*) FROM decision_log WHERE kind = 'phase-verification') ||
             ' accepted of 6 [source: decision_log phase-verification rows]'
      WHEN 'supervisor|execute'
        THEN 'by design (§1): the supervisor never executes; dispatch is user-approved text only [source: BUILD-SPEC §1]'
      WHEN 'supervisor|triage-learn'
        THEN 'rubric = db/queries/scoring rule; golden run is phase 4 [source: BUILD-SPEC §8 phase 3/4]'
      WHEN 'supervisor|persist-report'
        THEN 'decision_log + markdown mirrors live; briefs ship with phase 4 [source: state/ mirrors]'
      ELSE
        CASE WHEN ph.phase = 'execute'
             THEN 'pre-build; execute blocked: zero environments (' ||
                  (SELECT count(*) FROM environments) || ') + ' || i.owner_gate ||
                  ' [source: §3.4 map + owner_gate]'
             ELSE 'pre-build: no phase artifacts of its own yet [source: initiatives.status + milestones FK counts = ' ||
                  (SELECT count(*) FROM milestones m WHERE m.initiative_id = i.id) ||
                  ']' END
    END AS note
FROM initiatives i
CROSS JOIN (SELECT 'recon' AS phase UNION ALL SELECT 'build' UNION ALL SELECT 'execute'
            UNION ALL SELECT 'triage-learn' UNION ALL SELECT 'persist-report') AS ph;

CREATE VIEW IF NOT EXISTS v_score_inputs AS
WITH clocks AS (
    SELECT initiative_id,
           sum(state = 'live')             AS clock_live,
           sum(state = 'invalid')          AS clock_invalid,
           sum(state = 'never')            AS clock_never,
           sum(state = 'missing_evidence') AS clock_missing
    FROM staleness_clocks
    WHERE initiative_id IS NOT NULL
    GROUP BY initiative_id
),
caps AS (
    SELECT suite AS initiative_id,
           sum(approval_class = 'autonomous')                      AS cap_autonomous,
           sum(approval_class IN ('user_gated', 'gated_plus_1tr'))  AS cap_gated
    FROM capabilities
    GROUP BY suite
),
finds AS (
    SELECT e.initiative_id,
           count(*)                           AS finding_count,
           avg(CAST(f.score AS REAL))         AS finding_avg_score
    FROM evidence e
    JOIN findings f ON f.finding_ref = e.source_ref
    WHERE e.kind = 'finding'
    GROUP BY e.initiative_id
),
factors(factor, facts_ref) AS (
    VALUES
      ('clock_live',              'staleness_clocks.state=live'),
      ('clock_invalid',           'staleness_clocks.state=invalid'),
      ('clock_never',             'staleness_clocks.state=never'),
      ('clock_missing',           'staleness_clocks.state=missing_evidence'),
      ('cap_autonomous',          'capabilities.approval_class=autonomous'),
      ('cap_gated',               'capabilities.approval_class IN (user_gated,gated_plus_1tr)'),
      ('finding_count',           'findings via evidence.kind=finding'),
      ('finding_avg_score',       'avg(CAST(findings.score AS REAL))'),
      ('environments_registered','count(*) FROM environments (global readiness gate, §4.2)')
)
SELECT
    i.id AS initiative_id,
    f.factor,
    CASE f.factor
      WHEN 'clock_live'               THEN COALESCE(c.clock_live, 0)
      WHEN 'clock_invalid'            THEN COALESCE(c.clock_invalid, 0)
      WHEN 'clock_never'              THEN COALESCE(c.clock_never, 0)
      WHEN 'clock_missing'            THEN COALESCE(c.clock_missing, 0)
      WHEN 'cap_autonomous'           THEN COALESCE(cp.cap_autonomous, 0)
      WHEN 'cap_gated'                THEN COALESCE(cp.cap_gated, 0)
      WHEN 'finding_count'            THEN COALESCE(fn.finding_count, 0)
      WHEN 'finding_avg_score'        THEN COALESCE(fn.finding_avg_score, 0.0)
      WHEN 'environments_registered'  THEN (SELECT count(*) FROM environments)
    END AS value,
    f.facts_ref
FROM initiatives i
CROSS JOIN factors f
LEFT JOIN clocks c  ON c.initiative_id = i.id
LEFT JOIN caps   cp ON cp.initiative_id = i.id
LEFT JOIN finds  fn ON fn.initiative_id = i.id;
