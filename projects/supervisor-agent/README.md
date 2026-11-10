# supervisor-agent — "supervizor", the Portfolio Supervisor

A read-only-by-default decision layer across this portfolio's defensive capability
(`vuln_res/`, projects 1–3). It reads, computes, models, and recommends — it never
executes. The contract is `PROPOSAL.md`; this implementation is specified by
`BUILD-SPEC.md`. Runbook below; the escalation ladder is copied word for word from
`PROPOSAL.md` per BUILD-SPEC §7 (changing a single word is a new proposal, not an
edit).

## Runbook

All commands run from the repository root (or anywhere — paths resolve
relative to this project). SQL used by briefs lives only in `db/queries/`.

```sh
# Build / open the fused database (idempotent; safe to run twice)
python3 projects/supervisor-agent/tools/supervisor.py init

# §7 self-audit gate (exit 1 = FAIL; a FAIL suppresses any brief; every run is recorded)
python3 projects/supervisor-agent/tools/supervisor.py audit

# Provenance report: rows without provenance across provenance-bearing tables (must be all 0)
python3 projects/supervisor-agent/tools/supervisor.py provenance-null

# Record a decision (mirrors into state/decision-log.md at regeneration time)
python3 projects/supervisor-agent/tools/supervisor.py decide <kind> <outcome> <detail...>
```

Nothing here schedules, executes, or registers anything. Writing a schedule row
requires the user changing `approval_status` themselves (BUILD-SPEC §3.1
`schedules`).

## State layout

- `state/portfolio.db` — THE fused database; the single source of truth. Markdown
  under `state/` and everything in `briefs/` are regenerated views. If they disagree
  with the database, the database wins; the disagreement lands in `sync_violations`.
  The DB is committed with its WAL checkpointed, so no `-wal`/`-shm` files ever land.
- `db/schema.sql` — cumulative DDL, idempotent; `db/migrations/NNNN-*.sql` — the
  change history, applied in order, never edited after apply (ledger in `meta`).
- `ontology/sources.yaml` — every source a parser may read, with authority order.
  Add sources there first, never inline in parser code.
- `tests/self-audit.md` — the gate, run by `audit` and recorded to `audit_runs`.

## Escalation ladder (verbatim from PROPOSAL.md)

**Decides autonomously, no sign-off needed:**
- Which stale check to flag next, read from `knowledge/INDEX.md` timestamps and
  `progress/milestones.md`'s log (e.g. "the last `cargo audit` run was N days ago and a
  `Cargo.lock` change landed since — recon is due").
- Producing a `vulnres-reporting` rollup (read-only by that skill's own contract).
- Summarizing portfolio status to the user on request (reads across all the above, writes
  nothing).

**Always needs the user, every time, no matter how routine it starts to feel:**
- Creating or reusing any environment (same rule `vulnres-environment-runner` already
  enforces — the supervisor doesn't get a shortcut around it by being "just scheduling").
- Starting an actual fuzz campaign, exploit-dev session, or fleet SSH sweep (projects 1
  and 3) — the supervisor can *propose* "project 1 looks due," but the campaign itself
  still goes through that project's own sign-off gate.
- Anything that would cross from read-only measurement into mutation (project 2, once
  built) — 1TR + live owner confirmation, no exceptions, ever, regardless of how the
  request arrived (scheduled, supervisor-initiated, or direct).
- Anything that looks like it's drifting toward Apple-platform-security territory, per
  `vuln_res/CLAUDE.md`'s explicit "stop and ask" clause — the supervisor's job here is to
  **notice and surface it**, not silently redirect the work to something narrower that
  avoids the letter of the rule.
- Registering itself (or anything it dispatches to) as a live, standing scheduled job —
  "the supervisor decided this is due" is a recommendation to the user in this
  conversation, never a cron entry it creates on its own.

## Hard rule (BUILD-SPEC §0)

The supervisor reads, computes, models, and recommends. It never executes. Every verb
outside `read/parse/diff/score/rank/model/write supervisor-state/dispatch-with-approval`
is somebody else's job. The TTP simulation layer obeys the same rule: adversaries are
simulated as decision models and gap probes, never as tooling that runs anything.
