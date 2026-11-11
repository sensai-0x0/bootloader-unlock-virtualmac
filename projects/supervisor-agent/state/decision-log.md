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

## 2026-11-10T22:17:07Z — self-audit — pass

[]

## 2026-11-11T04:22:52Z — self-audit — pass

[]

## 2026-11-11T04:23:24Z — self-audit — pass

[]

## 2026-11-11T04:23:58Z — phase-verification — pass

Phase 5 verified -- TTP layer: pin, map, profile, simulate. (1) Verified the ATT&CK v20.1 release against REALITY before building anything against it: gh api confirmed the real mitre/cti GitHub release tag/date, and attack.mitre.org/resources/updates/ was fetched directly to confirm every specific claim BUILD-SPEC Sec5.2 makes (T1699/T1698/T1700/T1696/T1685.007/T1608.007/T1697, T1195.001 v2.0, G1059/G1058/G1045 v2.0/G0082 v4.0, C0064/C0066) -- all checked out against the real page, none fabricated. (2) Accept (a): downloaded the real enterprise-attack.json (49257997 bytes, sha256 f92e8ec8...ee0b042) into an isolated scratch directory (never committed to the repo -- build-time input only); pinned tag/url/sha in meta; recomputed the hash independently and confirmed an exact match. (3) Ingested the full real STIX bundle: 15 tactics, 867 techniques (all stored per Sec5.2's store-all rule), 1099 technique_tactics, 2166 technique_platforms, 4815 technique_groups, 1213 technique_campaigns, 706 technique_detcount rows -- all from real STIX relationships/objects, none synthesized. (4) Selection rubric (ttp/LIBRARY.md) applied via tools/ttp_ingest.py: 9 technique-surface mappings survived, scoped to real staleness_clocks/capabilities/build-trust/ingestion-path surfaces. Found and fixed a real bug surfaced by real data (Sec3.5 item 24): the Sec3.3 item 5 platform filter, applied literally, rejected T1698/T1699/T1685.007 (tagged SaaS/Windows only) and T1608.007 (tagged PRE) -- exactly the AI-enabled techniques Sec5.2 names as first-class. Fixed with two narrow, documented exceptions (PRE is ATT&CK's own platform-general tag; a 2-surface exemption for this portfolio's own non-OS-bound ingestion/capability surfaces) -- not a loosening of the filter itself. (5) Accept (b) proven twice: a direct SQL INSERT of verdict=covered with NULL evidence_id hit the schema's own CHECK constraint (exit 19, structurally impossible, not just application-level discipline); then a deliberately fabricated ttp/mappings.yaml entry (technique T1046, a nonsense evidence_anchor) was ingested, confirmed downgraded to asserted_unproven with a parse_failures row recording why, then removed from both the YAML and the live ttp_mappings table (parse_failures proof record kept, same convention as the existing mangled-milestones self-test). (6) Accept (c): three adversary profiles (patient-fleet, opportunistic-supplychain, agent-directed) seeded from ttp/profiles/*.md into tp_profiles; tools/simulate.py ran one scenario per profile (seed=1): patient-fleet 3 steps/2 gaps (including the exact ∞-latency-on-unmonitored-enrolled-Macs gap BUILD-SPEC Sec5.4 names verbatim), opportunistic-supplychain 2 steps/4 gaps, agent-directed 4 steps/3 gaps (including the exact what-validates-ingestion gap Sec5.3 names) -- every profile emitted >=1 honest gap probe, all traced to real staleness_clocks states and real (or honestly absent) capabilities, zero invented. Verified the unattested_preference caveat on patient-fleet's T1222 step is real (checked technique_groups: zero rows name T1222 for G1045 or any group). (7) Accept (d): self-audit v2 extended with EXECUTABLE_CONTENT_PATTERNS scanning ttp/*.md+*.yaml+profiles/*.md as files AND sim_steps/sim_gaps/sim_outcomes as DB text columns (check_sim_artifacts_executable) -- zero violations found; full audit passes. (8) Brief integration: briefs/2026-11-11-001-brief.md (brief_id=2) carries the new Simulate section (per-profile outcomes + top-3 gap probes by detection-latency severity) and TTP self-check line (0 structural violations, 0 scrutiny flags -- T1222's covered claim backed by real MITRE detcount=1/4, confirmed not a bug). (9) tests/phase5-accounting.txt committed; every new table ticked against the Sec3.4 map.
