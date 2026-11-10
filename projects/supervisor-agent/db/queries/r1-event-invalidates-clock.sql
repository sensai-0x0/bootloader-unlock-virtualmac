-- Rule R1 v2 — file-level implication: events invalidate dependent live clocks.
-- BUILD-SPEC §4.1. A commit/file event invalidates a live clock when (a) one of
-- the event's touched paths falls under one of the clock's `invalidates_on`
-- prefixes, and (b) the event postdates the clock's last verification at
-- LOCAL-DATE granularity: anchors are date-only strings authored in the
-- operator's local time, git event strings carry their own UTC offset, and
-- synthetic events are recorded in the same local-offset format (see
-- cmd_event), so substr(date-part) is the precision the evidence actually
-- supports. A same-day event that created the asserted claim does not
-- invalidate it; strictly later days do — content-level contradictions remain
-- R2's job. Verification time resolves from `last_verified_at` first; live
-- clocks whose currency is anchored by a parsed claim instead fall back to
-- `claim_anchors.asserted_at` via the clock's `last_verified_by` evidence.
-- A clock with no resolvable anchor is state 'never' and cannot be invalidated
-- — its absence IS the honest fact.
-- The invalidation history lands in clock_invalidation_events (append-only);
-- the second statement flips the clock's state to 'invalid' — a projection of
-- the history, never a content mutation.
-- BUILD-SPEC §4.1. A commit/file event invalidates a live clock when (a) one of
-- the event's touched paths falls under one of the clock's `invalidates_on`
-- prefixes, and (b) the event postdates the clock's last verification. The
-- verification time resolves from `last_verified_at` first; live clocks whose
-- currency is anchored by a parsed claim instead fall back to
-- `claim_anchors.asserted_at` via the clock's `last_verified_by` evidence.
-- A clock with NULL last_verified_at AND no claim anchor is state 'never' and
-- cannot be invalidated — its absence IS the honest fact.
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
JOIN events e ON
     substr(e.occurred_at, 1, 10) > COALESCE(
         substr(c.last_verified_at, 1, 10),
         (SELECT substr(ca.asserted_at, 1, 10) FROM claim_anchors ca
          WHERE ca.evidence_id = c.last_verified_by))
 AND COALESCE(
         substr(c.last_verified_at, 1, 10),
         (SELECT substr(ca.asserted_at, 1, 10) FROM claim_anchors ca
          WHERE ca.evidence_id = c.last_verified_by)) IS NOT NULL
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
  AND id IN (SELECT clock_id FROM clock_invalidation_events);
