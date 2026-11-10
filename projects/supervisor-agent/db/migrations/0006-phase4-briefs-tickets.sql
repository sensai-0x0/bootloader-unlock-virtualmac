-- Migration 0006 — phase 4: briefs, dispatch tickets, sharpened readiness.
-- BUILD-SPEC §8 phase 4 ("Briefs, tickets, sharpened implication; THE golden
-- run") and §3.1's "Human outputs" block.
--
-- v_score_inputs is redefined (not just extended) with two new factors that
-- phase 4's golden run surfaced as missing (§3.5 item 19): projects 1-3 all
-- carry a blanket owner_gate='user_gated' at seed time, so score_readiness
-- had no way to tell a software-only project (1) apart from one that
-- structurally needs 1TR (2) or enrolled fleet hardware (3) to make real
-- progress — exactly backwards from the PROPOSAL's own success metric
-- ("recon is current, fuzzing hasn't started... recommends project 1").
-- parsers.py's parse_project_lifecycle now classifies each project's real
-- owner_gate from its own PROPOSAL.md text; these two factors surface that
-- classification to the rubric. DROP + CREATE (not ALTER) because SQLite
-- views aren't altered in place and this is a genuine redefinition, not an
-- additive migration.

DROP VIEW IF EXISTS v_score_inputs;

CREATE VIEW v_score_inputs AS
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

-- ─── §3.1 "Human outputs" ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS briefs (
    id            INTEGER PRIMARY KEY,
    path          TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL,
    run_id        INTEGER NULL REFERENCES score_runs(id),
    do_next_top3  TEXT NOT NULL,   -- JSON list of initiative_ids, in rank order
    needs_human   TEXT NOT NULL    -- JSON list of {initiative_id, required_gate}
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

-- ─── v_phase_coverage wording fix (§3.5 item 22) ────────────────────────────
-- A real environment got registered between phase 3 and phase 4
-- (vm-sec-research-25d125, approved_for=[security-mode-measurement-research,
-- bputil-eval-live-tool-verification]) — the first time `environments` has
-- had a nonzero count since this view was written. Its two notes that
-- hardcoded the word "zero"/"(empty)" now print a literal self-contradiction
-- ("zero environments (1)"). The STATE itself ('blocked') stays correct: per
-- the registry's own rule (environments/SCHEMA.md: "approved_for is scoped,
-- not blanket"), this environment isn't approved for any of these four
-- initiatives' execute-phase work, so nothing about the blocking verdict
-- changes — only the wording, which must never claim zero when it isn't.
DROP VIEW IF EXISTS v_phase_coverage;

CREATE VIEW v_phase_coverage AS
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
