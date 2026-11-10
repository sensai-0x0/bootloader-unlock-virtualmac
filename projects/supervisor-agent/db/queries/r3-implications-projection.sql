-- Rule R3 — implication projection: generalizes every fired clock
-- invalidation (R1) into a typed row in `implications`
-- (event_id, effect_kind, effect_ref, rule_id), the shape BUILD-SPEC §3.1
-- groups with score_runs/recommendations under "Implication & ranking".
-- This is NOT a new inference — clock_invalidation_events remains the sole
-- authority on WHICH clocks flipped and WHEN; `implications` is the
-- queryable, extensible projection of that history so a later effect_kind
-- (e.g. a contradiction-driven effect) never requires touching R1 or
-- clock_invalidation_events again. Runs after r1/r2 in filename order
-- (tools/parsers.py run_implication globs r*.sql sorted); idempotent via
-- INSERT OR IGNORE against the table's own UNIQUE constraint.

INSERT OR IGNORE INTO provenance(source_ref, source_type, note)
VALUES ('projects/supervisor-agent/db/queries/r3-implications-projection.sql',
        'analysis_rule',
        'R3 projects clock_invalidation_events into implications at run time');

INSERT OR IGNORE INTO implications(event_id, effect_kind, effect_ref, rule_id, provenance_id)
SELECT
    cie.event_id,
    'clock_invalidated',
    c.surface,
    'R1',
    (SELECT id FROM provenance
     WHERE source_type = 'analysis_rule'
       AND source_ref = 'projects/supervisor-agent/db/queries/r3-implications-projection.sql'
     ORDER BY id DESC LIMIT 1)
FROM clock_invalidation_events cie
JOIN staleness_clocks c ON c.id = cie.clock_id;
