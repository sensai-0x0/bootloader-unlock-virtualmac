-- §4.3 deterministic scoring + ranking. Pivots ONLY v_score_inputs rows (the
-- canonical input set whose sorted rows feed score_runs.inputs_hash) — no
-- other table is read here, so "same inputs ⇒ same order" is a property of
-- this one query's data flow, not a hope (BUILD-SPEC §4.3, §3.5 item 14).
--
-- Four components, each clamped to the contract's 1-9 composite range:
--   score_staleness — urgency from decaying/never-verified clocks: invalid
--     and never/missing clocks count double a live one's baseline.
--   score_blast     — how much dispatchable capability surface depends on
--     this initiative's state (more registered capabilities = larger blast
--     radius if the state is wrong).
--   score_readiness — can work start right now without an unfulfillable
--     gate? An autonomous capability with live staleness work to react to
--     scores highest; a gated capability with zero registered environments
--     (the one hard blocker this portfolio currently has) scores honestly
--     low rather than pretending readiness it doesn't have.
--   score_precedent — established track record: initiatives with real,
--     scored findings outrank ones with none; no findings is the honest
--     baseline, not a zero that would out-rank a bad track record.
--
-- Ties break toward cheaper-to-start (§4.3): score_readiness DESC is the
-- secondary sort key (a readier item needs less setup to begin), then
-- initiative_id ASC as the final, fully deterministic tiebreak.
WITH pivot AS (
    SELECT
        initiative_id,
        max(CASE WHEN factor = 'clock_live'              THEN value END) AS clock_live,
        max(CASE WHEN factor = 'clock_invalid'            THEN value END) AS clock_invalid,
        max(CASE WHEN factor = 'clock_never'              THEN value END) AS clock_never,
        max(CASE WHEN factor = 'clock_missing'            THEN value END) AS clock_missing,
        max(CASE WHEN factor = 'cap_autonomous'           THEN value END) AS cap_autonomous,
        max(CASE WHEN factor = 'cap_gated'                THEN value END) AS cap_gated,
        max(CASE WHEN factor = 'finding_count'            THEN value END) AS finding_count,
        max(CASE WHEN factor = 'finding_avg_score'        THEN value END) AS finding_avg_score,
        max(CASE WHEN factor = 'environments_registered'  THEN value END) AS environments_registered
    FROM v_score_inputs
    GROUP BY initiative_id
),
scored AS (
    SELECT
        p.initiative_id,
        min(9, 1
            + 2 * COALESCE(p.clock_invalid, 0)
            + 1 * COALESCE(p.clock_never, 0)
            + 1 * COALESCE(p.clock_missing, 0))               AS score_staleness,
        min(9, 1 + COALESCE(p.cap_autonomous, 0) + COALESCE(p.cap_gated, 0)) AS score_blast,
        CASE
            WHEN COALESCE(p.cap_autonomous, 0) > 0
                 AND (COALESCE(p.clock_invalid, 0) + COALESCE(p.clock_never, 0)) > 0
                THEN 9
            WHEN COALESCE(p.cap_autonomous, 0) > 0
                THEN 6
            WHEN COALESCE(p.cap_gated, 0) > 0
                 AND COALESCE(p.environments_registered, 0) = 0
                THEN 1
            WHEN COALESCE(p.cap_gated, 0) > 0
                THEN 4
            ELSE 2
        END                                                    AS score_readiness,
        CASE
            WHEN COALESCE(p.finding_count, 0) = 0
                THEN 1
            ELSE min(9, 1 + CAST(round(COALESCE(p.finding_avg_score, 0)) AS INTEGER))
        END                                                    AS score_precedent
    FROM pivot p
)
SELECT
    initiative_id,
    score_staleness,
    score_blast,
    score_readiness,
    score_precedent,
    round((score_staleness + score_blast + score_readiness + score_precedent) / 4.0, 4) AS score_total,
    rank() OVER (
        ORDER BY (score_staleness + score_blast + score_readiness + score_precedent) DESC,
                 score_readiness DESC,
                 initiative_id ASC
    ) AS rnk
FROM scored
ORDER BY rnk, initiative_id;
