-- Rule R2 — currency-claim contradiction: knowledge entries that assert a
-- clean/cleared/no-vulnerabilities state ("currency claims") versus scored
-- findings recorded by a LATER sweep for the same initiative. Authority order
-- (sources.yaml): sweep findings outrank knowledge prose; the prose claim
-- loses, the finding wins, and history is preserved — the losing claim's
-- evidence row stays exactly where it is (§3.2: no facts are deleted).
-- Chronology: the knowledge claim's own asserted date (its `updated:` line,
-- parsed into claim_anchors) versus the contradicting finding's sweep date.
-- 'n/a (operational)' findings CAST to 0 and are excluded (they are not
-- defects, so they cannot contradict a clean bill).

INSERT OR IGNORE INTO provenance(source_ref, source_type, note)
VALUES ('projects/supervisor-agent/db/queries/r2-currency-contradiction.sql',
        'analysis_rule',
        'R2 evaluated at run time — see contradictory rows referencing this');

INSERT OR IGNORE INTO contradictions(
    losing_evidence_id, winning_evidence_id, rule_id, detected_at, detail,
    provenance_id, ingested_at)
SELECT
    ke.id,
    fe.id,
    'R2',
    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
    'R2: currency claim [' || ke.source_ref || '] (asserted ' || ca.asserted_at
      || ') vs finding [' || ff.finding_ref || '] (score '
      || CAST(ff.score AS INTEGER) || ', "' || ff.disposition
      || '") recorded by sweep ' || s.sweep_id || ' (' || s.started_at
      || ') — the claim loses; nothing deleted, the loser is marked here',
    (SELECT id FROM provenance
     WHERE source_type = 'analysis_rule'
       AND source_ref = 'projects/supervisor-agent/db/queries/r2-currency-contradiction.sql'
     ORDER BY id DESC LIMIT 1),
    strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
FROM evidence ke
JOIN claim_anchors ca ON ca.evidence_id = ke.id
JOIN initiatives i ON i.id = ke.initiative_id AND i.slug = 'vulnres_suite'
JOIN evidence fe ON fe.initiative_id = i.id AND fe.kind = 'finding'
JOIN findings ff ON ff.finding_ref = fe.source_ref
JOIN sweeps s ON s.id = ff.sweep_id
WHERE ke.kind = 'knowledge'
  AND ke.verdict_class = 'currency_claim'
  AND s.started_at > ca.asserted_at
  AND CAST(ff.score AS INTEGER) >= 1;
