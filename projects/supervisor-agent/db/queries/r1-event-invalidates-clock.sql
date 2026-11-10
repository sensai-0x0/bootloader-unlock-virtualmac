-- Rule R1 — file-level implication: events invalidate dependent live clocks.
-- BUILD-SPEC §4.1. A commit/file event invalidates a live clock when (a) one of
-- the event's touched paths falls under one of the clock's `invalidates_on`
-- prefixes, and (b) the event postdates the clock's last verification
-- (`claim_anchors`/`last_verified_at`). A clock with NULL last_verified_at is
-- state 'never' and cannot be invalidated — its absence IS the honest fact.
-- The invalidation history lands in clock_invalidation_events (append-only);
-- the second statement flips the clock's state to 'invalid' — a projection of
-- the history, never a content mutation.
-- LIKE-prefix note: `invalidates_on` entries are plain path prefixes authored
-- in tools/parsers.py seed_clocks(); none contain LIKE wildcards, and a
-- malicious-pattern change is caught because clocks are provenance-keyed rows
-- whose invalidates_on is reviewable in diffs.

INSERT OR IGNORE INTO clock_invalidation_events(clock_id, event_id, fired_at)
SELECT c.id, e.id, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
FROM staleness_clocks c
JOIN events e ON e.occurred_at > c.last_verified_at
             AND c.last_verified_at IS NOT NULL
             AND c.state = 'live'
WHERE EXISTS (
        SELECT 1
        FROM json_each(c.invalidates_on) cp, json_each(e.paths) ep
        WHERE ep.value LIKE cp.value || '%'
      )
  AND NOT EXISTS (SELECT 1 FROM clock_invalidation_events cie
                  WHERE cie.clock_id = c.id AND cie.event_id = e.id);

UPDATE staleness_clocks
SET state = 'invalid'
WHERE state = 'live'
  AND last_verified_at IS NOT NULL
  AND id IN (SELECT clock_id FROM clock_invalidation_events);
