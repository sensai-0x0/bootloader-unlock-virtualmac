-- Phase 5 simulation: answers the three coverage questions (detect? limit?
-- how fast?) for one technique, joining ttp_mappings + staleness_clocks (by
-- surface match) + capabilities. BUILD-SPEC §5.4 step 2. Takes one bound
-- parameter: technique_id.
SELECT
    m.surface,
    m.verdict,
    m.detect_via,
    m.limit_via,
    m.evidence_id,
    sc.state            AS clock_state,
    sc.last_verified_at AS clock_last_verified_at,
    c.name              AS capability_name,
    c.approval_class    AS capability_approval_class
FROM ttp_mappings m
LEFT JOIN staleness_clocks sc ON sc.surface = m.surface
LEFT JOIN capabilities c ON c.id = m.capability_id
WHERE m.technique_id = ?
ORDER BY m.surface;
