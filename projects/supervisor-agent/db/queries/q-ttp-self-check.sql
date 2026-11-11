-- §5.5 "TTP self-check": verdict/evidence coherence per mapping row. The
-- schema's CHECK already makes 'covered' + NULL evidence structurally
-- impossible to insert at all (§3.3 item 2, re-verified this phase by a
-- direct SQL insert attempt — see decision_log) — this query is the audit
-- that proves that invariant holds at read time too, plus the one thing
-- the schema can't pre-verify: a 'covered' claim on a technique MITRE
-- itself documents zero detection strategies for (extra scrutiny, §3.3
-- item 7).
SELECT
    t.attack_id,
    m.surface,
    m.verdict,
    m.evidence_id,
    COALESCE(dc.det_strategies, 0) AS det_strategies,
    CASE WHEN m.verdict = 'covered' AND m.evidence_id IS NULL
         THEN 1 ELSE 0 END AS structural_violation,
    CASE WHEN m.verdict = 'covered' AND COALESCE(dc.det_strategies, 0) = 0
         THEN 1 ELSE 0 END AS scrutiny_flag
FROM ttp_mappings m
JOIN techniques t ON t.id = m.technique_id
LEFT JOIN technique_detcount dc ON dc.technique_id = t.id
ORDER BY t.attack_id;
