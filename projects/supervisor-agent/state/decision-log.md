# Decision log

Regenerated view of `decision_log` in `state/portfolio.db` — never edited
by hand. If this mirror and the database disagree, the database wins and
the mismatch goes to `sync_violations` (§3.2).

## 2026-11-10T16:02:44Z — phase-verification — pass

Phase 2 verified. (1) Full fusion: sources 1-7 all parse ok on a fresh DB at db_version 4 (run 1): 11 milestones, 10 milestone_log entries, 16 links, 55 evidence rows, 33 git events, 7 capabilities, 3 sweeps, 5 findings, 0 exploits by construction. (2) Clock table requirement: 8 clocks seeded (5 live / 3 never); R1 v2 (local-date granularity + claim_anchors fallback) invalidates 4 live knowledge clocks from real commits whose local date postdates the 2026-11-10 anchors (event 19 scripts/+src/, event 20 .claude/agents/); base verified state = 1 live + 3 never + 4 invalid, each invalidator matching its clock prefix list. (3) Synthetic git event 34 (kind=synthetic, described Cargo.lock merge, nothing executed) flips live clock knowledge:cargo-audit-clean to invalid on regeneration - exactly 1 new invalidation. (4) R2 currency contradictions: 6 rows, including verify-baseline-no-size-cap from sweep 2026-11-11-001 vs clean-as-of knowledge entries (build-test-clippy-fmt-clean asserted 2026-11-10, command-enum note, cargo-audit note). (5) Typed evidence kinds parse per INDEX.md footer: currency_claim typed rows with asserted_at claim anchors (3), environment footer flag surfaced. (6) Accounting query output committed as tests/phase2-accounting.txt and every zero-row table ticked against the SS3.4 map: exploits=0 (EMPTY by construction), environments=0 (no approved environment), fuzz_targets=0 (project 1 pre-build), fleet_enrollments=0 (project 3 pre-build), schedules=0 (approval is a user act), cadence_reports=0 (no cadence run yet), parse_failures=0, decision_log=0 at capture time, audit_runs=0 at capture time. Evidence trail: state/portfolio.db run 1-2, contradiction rows 1-6, clock_invalidation_events 5 rows total.

## 2026-11-10T16:02:48Z — self-audit — pass

[]

## 2026-11-10T16:03:30Z — self-audit — pass

[]
