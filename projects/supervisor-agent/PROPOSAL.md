# Supervisor agent — the orchestration layer spanning this portfolio

**One-line pitch:** a read-only-by-default coordinator that decides, across the three new
projects and the existing `vuln_res/` suite, what's stale and what runs next — without
ever gaining authority none of the underlying agents already have.

## APT-mindset framing

A patient adversary operating against a fleet doesn't run one tool once; it runs a
standing program — recon, then exploitation, then persistence, then expansion — and
*decides* which phase to invest in next based on what's working and what the defender
seems blind to. The defensive inversion isn't "build an attacker's C2" — it's "build the
equivalent decision layer for legitimate, bounded defensive work": something that looks
across all the defensive capability this repo has (static analysis, fuzzing, fleet
monitoring, evidence) and decides what's gone stale, what a recent code change implicates,
and what's worth a human's attention next — the same "which bug deserves attention first"
instinct `vulnres-triage`'s scoring rubric already applies to individual findings, raised
one level to apply to entire initiatives.

## Relationship to `vulnres-orchestrator` (read that file first — this doesn't duplicate it)

`.claude/agents/vulnres-orchestrator.md` already does real orchestration — but strictly
*within* `vuln_res/`: given the six stage agents (recon, fuzz-harness, environment-runner,
triage, exploit-dev, disclosure), it decides which to invoke, in what order, for **one
sweep**. It reads `vuln_res/knowledge/INDEX.md` and `vuln_res/sweep-reports/` to decide a
sweep's shape, and that's its entire world.

The supervisor agent proposed here sits **one layer above that**, with a wider world:

| | `vulnres-orchestrator` | supervisor agent (this proposal) |
|---|---|---|
| Scope | One `vuln_res/` sweep | The whole `projects/` portfolio + `vuln_res/` |
| Reads | `vuln_res/knowledge/`, `vuln_res/sweep-reports/` | The above, plus `progress/milestones.md`, each project's own status file (once projects 1–3 exist), `vuln_res/knowledge/environments/INDEX.md` |
| Decides | Which of 6 *stage* agents to run, in what order | Which *project* needs attention next (a fuzz sweep? a fleet drift check? static recon on a PR?), then hands off to that project's own coordinator (`vulnres-orchestrator` for `vuln_res/` work, a project-specific runner for 3 and 3) |
| Executes anything itself | No — dispatches to stage agents | No — dispatches to `vulnres-orchestrator` or a project runner; never calls `wrapper.rs`-equivalent code itself |

It does not replace `vulnres-orchestrator`, duplicate its logic, or reach into `vuln_res/`
internals directly — it treats "run a `vuln_res/` sweep" as one opaque unit of work it can
schedule, the same way it would treat "run a fleet drift check" (project 3) as another.
This keeps the existing, already-built orchestrator's scope exactly as documented, and
avoids the trap `vuln_res/plans/06-orchestration-and-scheduling.md` already named for why
this suite isn't one monolithic agent: different cadences, different tool dependencies,
different approval boundaries, collapsed into one agent either over-triggers the
expensive stuff or under-triggers the cheap stuff.

## Scope contract

**Read-only by default**, across:
- `vuln_res/knowledge/`, `vuln_res/sweep-reports/` (existing)
- `progress/goal.md`, `progress/milestones.md` (existing — the M8–M10 track record)
- Each project's own status file, once projects 1–3 are built (new — see each
  `PROPOSAL.md`'s phase 1 for exactly what that file should contain)
- `vuln_res/knowledge/environments/INDEX.md` — to know what's currently approved, never
  to create or reuse an environment itself

**Anything beyond reading is a dispatch, never a direct action.** The supervisor agent
never calls `wrapper.rs`, never runs `cargo fuzz`, never SSHes into a fleet Mac, never
drafts a PR itself. It picks the next unit of work and hands it to the agent/skill already
built for that unit — `vulnres-orchestrator` for a `vuln_res/` sweep, `vulnres-reporting`
for a cadence rollup, a project-specific runner (once built) for projects 1 and 3. This
means the supervisor inherits every guardrail its dispatch targets already enforce —
it cannot grant itself new authority by existing one layer up.

## Escalation ladder

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

## Known harness constraint this proposal inherits

Project-level `.claude/agents/*.md` (including every `vulnres-*` definition this proposal
depends on) isn't discovered by this harness's native `subagent_type` dispatch — confirmed
and root-caused in `vuln_res/sweep-reports/2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md`,
with the working fallback documented in `vuln_res/plans/06-orchestration-and-scheduling.md`.
Until that's fixed upstream, "running the supervisor" means the coordinating session (or a
`fork` of it) reads this file directly and dispatches per its logic — exactly the same
pattern already in use for `vulnres-orchestrator` today. This proposal does not assume the
gap is fixed; building the supervisor doesn't require it to be.

## What this is not

Not a new capability. Not a new authority. Not a thing that runs on its own schedule
without the user's standing approval for that schedule. It is a decision layer over
capability that already exists or that projects 1–3 would add — its entire value is
"notice what's stale and say so," never "act on it unilaterally."

## Open risk

The biggest risk with any supervisor-shaped agent is scope creep — it's tempting to let
"decide what's next" quietly become "do what's next." The escalation ladder above exists
specifically to keep that from happening; any future change to this proposal that blurs
the read-only/dispatch-only line should be treated as a new proposal requiring its own
sign-off, not an incremental extension of this one.

## Success metric

Given the current, real state of this repo (multiple closed static-analysis/recon sweeps,
no fuzz target built, no environment registered), a supervisor run correctly identifies
"recon is current, fuzzing hasn't started, no fleet project exists yet" and recommends
project 1 as the next concrete step — without executing anything itself.
