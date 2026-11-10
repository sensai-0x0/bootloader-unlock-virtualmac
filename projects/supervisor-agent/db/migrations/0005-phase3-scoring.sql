-- Migration 0005 — phase 3: deterministic scoring + phase-coverage map.
-- BUILD-SPEC §4.2/§4.3, §3's staleness_clocks → score_runs → recommendations
-- chain. Two rules hold:
--   (1) the rubric and every input it consults live as reviewed SQL —
--       v_score_inputs is the canonical input set (the inputs_hash is taken
--       over its rows), and q-scoring.sql pivots ONLY those rows — so
--       "same inputs ⇒ same order" is a property of the data flow
--       (§3.5 item 14), not a hope.
--   (2) recommendations is append-only per score_run; verification is a
--       separate read-only run against the stored rows (score_runs.inputs_hash
--       is UNIQUE, so an identical state can record its run only once —
--       §3.5 item 15).

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
    brief_id             INTEGER NULL,  -- FK deferred to phase 4; briefs do not exist yet (§3.5 item 16)
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

-- ─── §4.2 phase-coverage map ────────────────────────────────────────────────
-- One row per initiative×phase. States are §4.2's green/stale/never-run plus
-- two facts the data forced (§3.5 item 17): 'in-progress' (parsed, real
-- progress exists but unresolved) and 'blocked' (a structural, state-level
-- blocker — e.g. zero registered environments — not a judgment). Every note
-- names its source. Hand-authored mapping lives HERE, as reviewed SQL, never
-- in rendering code.
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

-- ─── §4.3 canonical scoring inputs ─────────────────────────────────────────
-- EVERY factor row the rubric (q-scoring.sql) consumes — one row per
-- initiative×factor, zeros included, so the canonical hash covers absence as
-- well as presence (§4.3's "same inputs ⇒ same order" is a property of this
-- flat, exhaustive row set, not a hope). facts_ref names the backing
-- table/expression — the provenance of the ranking, component by component
-- (q-scoring.sql's COMPONENT_FACTORS grouping, mirrored in tools/supervisor.py).
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
