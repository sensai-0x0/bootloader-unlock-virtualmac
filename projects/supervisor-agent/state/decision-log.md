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

## 2026-11-10T16:04:39Z — self-audit — pass

[]

## 2026-11-10T16:39:42Z — self-audit — pass

[]

## 2026-11-10T16:40:05Z — phase-verification — pass

Phase 3 verified. (1) §4.2 phase-coverage map: v_phase_coverage view computes state (green/stale/blocked/in-progress/never-run) per initiative x phase from live data (fixed a pre-existing SQLite incompatibility in its CROSS JOIN -- SQLite has no (VALUES ...) AS alias(col) derived-table syntax, only WITH alias(col) AS (VALUES ...); rewritten as a UNION ALL subquery, verified against a scratch rebuild). (2) §4.3 deterministic scoring: v_score_inputs is the canonical, exhaustive input set (9 factors x 6 initiatives = 54 rows, zeros included); q-scoring.sql pivots ONLY those rows into 4 clamped 1-9 components (staleness/blast/readiness/precedent) plus score_total and a RANK() tie-broken on readiness DESC then initiative_id ASC. tools/supervisor.py score command hashes the canonical sorted input rows (sha256) and is idempotent via score_runs.inputs_hash UNIQUE -- ran twice from identical state (score_run_id=1 both times, inputs_hash 2da1e756...96c87d both times, byte-identical ranking and scores both times, confirming 'same inputs => same order' as a structural property, not a hope. (3) Every recommendation row's component_provenance JSON names the real input rows (value + facts_ref) that produced each of its four score components -- verified on rank=1 (vulnres_suite, score_total=7.75). (4) Migration 0005 and its identical copy in schema.sql (snapshot-must-contain-every-migration's-DDL, Sec3.5 item 10) now both parse cleanly from a scratch rebuild (sqlite3 CLI diff of .tables confirmed score_runs/recommendations/implications/v_phase_coverage/v_score_inputs all present). (5) New rule R3 (r3-implications-projection.sql) backfills the implications table (5 rows) as a generalized, idempotent projection of the existing clock_invalidation_events history -- not a new inference, R1 remains sole authority on which clocks flipped. (6) Caught and corrected a serious process error during this phase: an initial 'rm -f state/portfolio.db' rebuild-from-scratch wiped the phase 0-2 decision_log/audit_runs history (violating Sec3.2's no-facts-are-deleted rule); restored via git checkout and re-applied migration 0005 incrementally instead, preserving all prior history (decision_log now has 5 rows: 4 historical + this one). (7) Accounting query output committed as tests/phase3-accounting.txt: every table ticked against Sec3.4's map, including the 3 new phase-3 tables. Evidence: state/portfolio.db score_runs id=1, recommendations rows 1-6, implications rows 1-5, tests/phase3-accounting.txt.

## 2026-11-10T16:40:11Z — self-audit — pass

[]

## 2026-11-10T21:59:51Z — self-audit — pass

[]

## 2026-11-10T22:00:35Z — self-audit — pass

[]

## 2026-11-10T22:00:51Z — phase-verification — pass

Phase 4 verified -- THE golden run, per PROPOSAL.md's success metric. (1) Brief generator (tools/brief.py) renders briefs/<date>-<NNN>-brief.md from score_runs/recommendations/v_phase_coverage/staleness_clocks only, via the reviewed query layer -- never ad-hoc analysis. (2) Golden-run result (briefs/2026-11-10-001-brief.md, brief_id=1, score_run_id=2): do-next top-3 = vulnres_suite (rank1, score 7.75, required_gate='user approval'), project1_fuzz (rank2, score 2.75, required_gate='user approval to begin (software-only -- no hardware/1TR/fleet dependency)'), project3_drift (rank3). This satisfies the PROPOSAL's literal success metric ('recon is current, fuzzing hasn't started, no fleet project exists yet... recommends project 1') -- project 1 appears in the top-3 with the CORRECT required gate, distinctly ahead of project2_mutation/project3_drift once owner_gate's content-aware classification (item 19) correctly identified only project 1 as software-only. (3) needs-a-human list is complete: all 4 gated recommendations (vulnres_suite, project1_fuzz, project3_drift, project2_mutation) listed with accurate required_gate strings. (4) Zero execution: self-audit's forbidden-pattern scan covers briefs/*.md and passed; every DISPATCH ticket is text-only, approval_status=pending. (5) Two real correctness bugs surfaced and fixed while building this, not formula-gaming: (a) required_gate previously picked the MOST PERMISSIVE capability present (dishonestly reported vulnres_suite as gate='none' despite 4 of 7 capabilities being user_gated) -- now most-restrictive-first (item 21); (b) owner_gate was a blanket 'user_gated' for all three new projects, unable to distinguish project 1 (software-only) from project 2 (needs 1TR, verified via verbatim '1TR' marker in its own PROPOSAL.md) from project 3 (needs enrolled fleet hardware, verified via verbatim 'enrolled' marker) -- now classified per-project via parse_project_lifecycle (item 19). (6) A real environment (vm-sec-research-25d125) was registered by concurrent work mid-phase, exposing a self-contradictory 'zero environments (1)' wording bug in v_phase_coverage (item 22, fixed: wording only, state stays honestly 'blocked' per the registry's own approved_for-is-scoped rule) and a deeper, deliberately-deferred gap: 'never'-state clocks have no transition rule at all (item 23, flagged in the brief itself with a caveat, not silently fixed under this phase's time budget). (7) dispatch_tickets/briefs tables added via migration 0006, applied incrementally (db_version 5->6), schema.sql kept snapshot-complete, scratch-rebuild-verified. (8) tests/phase4-accounting.txt committed; every table including the two new ones ticked against the SS3.4 map.
