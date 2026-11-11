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

-- v_phase_coverage (phase 4 wording fix — matches migration 0006, §3.5 item
-- 22: a real environment got registered between phase 3 and 4; its two
-- notes hardcoded the word "zero"/"(empty)" and now print a literal
-- self-contradiction. The STATE stays 'blocked' — per environments/
-- SCHEMA.md's own rule ("approved_for is scoped, not blanket"), the one
-- registered environment isn't approved for any of these four initiatives'
-- execute-phase work — only the wording changed.)
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
        THEN (SELECT count(*) FROM environments) ||
             ' environment(s) registered, none approved for vulnres_suite''s execute-phase work ' ||
             '(registry rule: approved_for is scoped, not blanket) → structurally blocked; §4.2 state fact ' ||
             '[source: environments registry]'
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
             THEN 'pre-build; execute blocked: ' ||
                  (SELECT count(*) FROM environments) ||
                  ' environment(s) registered, none approved for this initiative''s execute-phase work; owner_gate=' ||
                  COALESCE(i.owner_gate, 'NULL') ||
                  ' [source: §3.4 map + environments registry + owner_gate]'
             ELSE 'pre-build: no phase artifacts of its own yet [source: initiatives.status + milestones FK counts = ' ||
                  (SELECT count(*) FROM milestones m WHERE m.initiative_id = i.id) ||
                  ']' END
    END AS note
FROM initiatives i
CROSS JOIN (SELECT 'recon' AS phase UNION ALL SELECT 'build' UNION ALL SELECT 'execute'
            UNION ALL SELECT 'triage-learn' UNION ALL SELECT 'persist-report') AS ph;

-- v_score_inputs (phase 4 redefinition — matches migration 0006; see that
-- file's header for why owner_gate_set/hw_gate_present were added).
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
      ('environments_registered','count(*) FROM environments (global readiness gate, §4.2)'),
      ('owner_gate_set',          'initiatives.owner_gate IS NOT NULL (projects 1-3 only)'),
      ('hw_gate_present',         'initiatives.owner_gate IN (user_gated_plus_1tr,user_gated_fleet_hardware)')
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
      WHEN 'owner_gate_set'           THEN CASE WHEN i.owner_gate IS NOT NULL THEN 1 ELSE 0 END
      WHEN 'hw_gate_present'          THEN CASE WHEN i.owner_gate IN
                                              ('user_gated_plus_1tr', 'user_gated_fleet_hardware')
                                            THEN 1 ELSE 0 END
    END AS value,
    f.facts_ref
FROM initiatives i
CROSS JOIN factors f
LEFT JOIN clocks c  ON c.initiative_id = i.id
LEFT JOIN caps   cp ON cp.initiative_id = i.id
LEFT JOIN finds  fn ON fn.initiative_id = i.id;

-- ─── phase 4 (cumulative snapshot continuation — matches migration 0006) ────
-- §3.1 "Human outputs"

CREATE TABLE IF NOT EXISTS briefs (
    id            INTEGER PRIMARY KEY,
    path          TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL,
    run_id        INTEGER NULL REFERENCES score_runs(id),
    do_next_top3  TEXT NOT NULL,
    needs_human   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dispatch_tickets (
    id                INTEGER PRIMARY KEY,
    brief_id          INTEGER NOT NULL REFERENCES briefs(id),
    capability_id     INTEGER NULL REFERENCES capabilities(id),
    scope_invariants  TEXT NOT NULL,
    required_gate     TEXT NOT NULL,
    approval_status   TEXT NOT NULL DEFAULT 'pending'
                      CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approved_by       TEXT NULL,
    approved_at       TEXT NULL,
    executed_at       TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_dispatch_tickets_brief ON dispatch_tickets(brief_id);


-- ────────────────────────────────────────────────────────────────────────
-- phase 5 (cumulative snapshot continuation — matches migration 0007)

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
