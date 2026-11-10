-- §3.4 suite-completeness accounting: every table, its row count, and the
-- BUILD-SPEC §3.4 map family that owns it. An honestly-empty table is EXPECTED
-- until its family produces artifacts — the zero is the fact, not a gap.
-- Run by tools/supervisor.py at every phase boundary; output is committed as a
-- decision-log attachment with every zero ticked against this map.

SELECT 'provenance'        AS table_name, (SELECT count(*) FROM provenance)        AS rows, 'supervisor backbone (§3.1)'            AS map_family
UNION ALL SELECT 'meta',               (SELECT count(*) FROM meta),               'supervisor backbone / goal peg (§3.4)'
UNION ALL SELECT 'runs',               (SELECT count(*) FROM runs),               'supervisor backbone / own outputs (§3.4)'
UNION ALL SELECT 'decision_log',       (SELECT count(*) FROM decision_log),       'supervisor backbone / own outputs (§3.4)'
UNION ALL SELECT 'audit_runs',         (SELECT count(*) FROM audit_runs),         'supervisor own outputs (§3.4)'
UNION ALL SELECT 'parse_failures',     (SELECT count(*) FROM parse_failures),     'honest-degradation records (§2.2)'
UNION ALL SELECT 'initiatives',        (SELECT count(*) FROM initiatives),        'portfolio goal + projects 1–3 defs (§3.4)'
UNION ALL SELECT 'evidence',           (SELECT count(*) FROM evidence),           'durable knowledge entries + sweep summaries (§3.4)'
UNION ALL SELECT 'claim_anchors',      (SELECT count(*) FROM claim_anchors),      'knowledge claim chronology (phase-2 build-time amendment)'
UNION ALL SELECT 'milestones',         (SELECT count(*) FROM milestones),         'milestone status (§3.4)'
UNION ALL SELECT 'milestone_log',      (SELECT count(*) FROM milestone_log),      'milestone dated log / Next up (§3.4)'
UNION ALL SELECT 'links',              (SELECT count(*) FROM links),              'object/link definitions (ontology/SCHEMA.md)'
UNION ALL SELECT 'sweeps',             (SELECT count(*) FROM sweeps),             'sweep programs run so far (§3.4)'
UNION ALL SELECT 'findings',           (SELECT count(*) FROM findings),           'individual findings (§3.4)'
UNION ALL SELECT 'exploits',           (SELECT count(*) FROM exploits),           'weaponized/developed exploits (§3.4) — EMPTY by construction'
UNION ALL SELECT 'environments',       (SELECT count(*) FROM environments),       'environment registry (§3.4) — read-only mirror; a nonzero count is not approval for any specific initiative (approved_for is scoped, not blanket)'
UNION ALL SELECT 'capabilities',       (SELECT count(*) FROM capabilities),       'the 6 stage agents + orchestrator + skills (§3.4)'
UNION ALL SELECT 'cadence_reports',    (SELECT count(*) FROM cadence_reports),    'cadence rollups (§3.4)'
UNION ALL SELECT 'fuzz_targets',       (SELECT count(*) FROM fuzz_targets),       'fuzz targets (§3.4) — EMPTY until project 1 builds its first'
UNION ALL SELECT 'fleet_enrollments',  (SELECT count(*) FROM fleet_enrollments),  'fleet enrollment list (§3.4) — EMPTY, project 3 pre-build'
UNION ALL SELECT 'schedules',          (SELECT count(*) FROM schedules),          'approved standing schedules (§3.4) — EMPTY: approval is a user act'
UNION ALL SELECT 'staleness_clocks',   (SELECT count(*) FROM staleness_clocks),   'staleness clocks (§3.1)'
UNION ALL SELECT 'events',             (SELECT count(*) FROM events),             'git event stream (§3.4 source 6)'
UNION ALL SELECT 'clock_invalidation_events', (SELECT count(*) FROM clock_invalidation_events), 'computed implication history (§3.2)'
UNION ALL SELECT 'contradictions',     (SELECT count(*) FROM contradictions),     'corrections-as-rows (§3.2)'
UNION ALL SELECT 'score_runs',         (SELECT count(*) FROM score_runs),         'deterministic scoring anchors (§3.1 phase 3)'
UNION ALL SELECT 'recommendations',    (SELECT count(*) FROM recommendations),    'ranked decision-brief lines (§3.1); brief_id backfilled once a phase-4 brief cites the score_run'
UNION ALL SELECT 'implications',       (SELECT count(*) FROM implications),       'generalized effect rows projected from clock invalidations (R3, phase 3)'
UNION ALL SELECT 'briefs',             (SELECT count(*) FROM briefs),              'generated decision briefs (§3.1 phase 4 "Human outputs")'
UNION ALL SELECT 'dispatch_tickets',   (SELECT count(*) FROM dispatch_tickets),    'text-only DISPATCH proposals per brief (§3.1 phase 4) — EMPTY approved_by: approval is a user act, never automated'
ORDER BY table_name;
