-- §5.4 step 3 / §5.5: top gap probes by detection-latency math across every
-- sim_gaps row raised_into_brief=1. Severity order: never-clock (infinite
-- latency, BUILD-SPEC's own worked example) > invalid-clock (unknown/stale)
-- > no-clock-at-all (unknown, never measured) > anything else.
SELECT
    g.id, g.question, g.verdict, p.name AS profile_name,
    CASE
      WHEN g.question LIKE '%clock state=never%' THEN 3
      WHEN g.question LIKE '%clock state=invalid%' THEN 2
      ELSE 1
    END AS severity
FROM sim_gaps g
JOIN sim_steps s ON s.id = g.step_id
JOIN sim_scenarios sc ON sc.id = g.scenario_id
JOIN tp_profiles p ON p.id = sc.profile_id
WHERE g.raised_into_brief = 1
ORDER BY severity DESC, g.id
LIMIT 3;
