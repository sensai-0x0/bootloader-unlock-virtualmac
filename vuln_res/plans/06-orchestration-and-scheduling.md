# 06 — Orchestration and scheduling

How plans `01`–`05` actually run as a connected pipeline rather than five scripts someone
has to remember to chain by hand.

## Trigger model

Three different cadences, not one:

1. **On every PR touching `src/state/img4.rs`, `src/main.rs`'s `cmd_verify`, or
   `scripts/ci_guards.sh`** — run `01`'s static-analysis agent (fast, no sandbox needed)
   as a CI check, same tier as the existing `cargo clippy`/`cargo fmt --check` gates in
   `../../CLAUDE.md`'s "Commands" section. This is the cheap, fast feedback loop.
2. **On a schedule (weekly is reasonable to start)** — `01`'s dependency/SBOM scan
   (`cargo audit`/`cargo deny`), since new advisories appear independent of any code
   change here.
3. **On demand, explicitly requested** — the full `02` → `03` → `04` → `05` fuzzing
   pipeline. This is not a "run on every commit" thing: it needs a sandboxed environment
   (`03`) that itself needs user sign-off to create, and a multi-minute-to-hours campaign
   isn't CI-gate material. Treat it like the root project treats `apply`/`revert` — a
   deliberate, asked-for action, not an automatic one.

## Agent handoff contract

Each stage writes its output to a fixed location the next stage reads from, so the
pipeline can be resumed or re-run at any stage without re-doing earlier work:

| Stage | Writes to | Next stage reads from |
|---|---|---|
| `01` | `vuln_res/sweep-reports/<sweep-id>/<slug>.md` | (terminal — these are usually just filed as issues/PRs directly) |
| `02` | `fuzz/fuzz_targets/*.rs`, `fuzz/corpus/*` | `03` |
| `03` | `fuzz/artifacts/<target>/*` (inside the sandbox; copied out after teardown) | `04` |
| `04` | `vuln_res/sweep-reports/<sweep-id>/<target>-<hash>.md` + minimized PoC fixture | `05` |
| `05` | A PR, an upstream issue link, or an escalation note, appended to the same finding file | (terminal) |

## Why this isn't one monolithic "vuln-research" agent

Each stage has a different tool dependency (clippy vs. cargo-fuzz vs. a sandbox runtime),
a different cadence (CI-gate vs. weekly vs. on-demand), and a different approval boundary
(fully automatic vs. "ask before installing a sandbox tool" vs. "a human reviews every
fix PR before merge"). Collapsing them into one agent would either over-trigger the
expensive stages on every commit, or under-trigger the cheap ones by batching everything
behind the slow stage's cadence. Keeping them separate, per this folder's `plans/README.md`
diagram, is what makes "quickly evaluating vulnerabilities" actually quick for the cheap
stages while still gating the expensive, sandbox-requiring ones properly.

## How to actually invoke this suite today (subagent-registry workaround)

**Confirmed gap, root-caused 2026-11-10** (see
`../sweep-reports/2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md`):
this harness's Agent tool only loads subagent types from the **global, user-level**
`~/.claude/agents/` directory. Project-level `.claude/agents/*.md` files — the actual
`vulnres-*` definitions this suite is built from — are never discovered, in *any* project
under this monorepo, not just this one (`sensai-stack`, `parit-architecture`, and
`compilar-v0.5` all have the same kind of unused project-level `.claude/agents/`
directory). This was confirmed by diffing the Agent tool's "available agents" error
message against `ls ~/.claude/agents/`: they match exactly. It is not a staleness or
session-restart issue (retested after `/clear` with the files committed — same result),
and it's been filed as harness feedback. Don't keep retrying `subagent_type:
"vulnres-*"` expecting a different result until that's actually fixed upstream.

**Until it is, invoke each stage like this instead** — functionally equivalent, and keeps
the agent definitions themselves project-scoped (they stay as files in *this* repo's
`.claude/agents/`, never copied into the global directory just to make them callable):

```
Agent({
  subagent_type: "general-purpose",
  description: "<stage name> sweep",
  prompt: "You are acting as the vulnres-<stage> agent defined at
    .claude/agents/vulnres-<stage>.md in this repo
    (/Users/nullzero/Metacogna/the-ant-experiment). Read that file in full and follow it
    exactly — including its own instruction to read vuln_res/CLAUDE.md first. Then:
    <the specific task for this sweep, e.g. 'run a fresh recon pass per plan 01'>."
})
```

A fresh `general-purpose` agent has no memory of this definition, so the prompt must
name the exact file path — it reads its own marching orders from disk rather than having
them injected by the harness, which is the whole workaround. The coordinating session
(or a `fork` of it, when the stage doesn't need isolation from the current context)
dispatches this instead of a native `subagent_type`, one stage at a time, following the
same handoff contract (table above) either way.

`vulnres-orchestrator` itself is just another `.claude/agents/*.md` file under this same
constraint — "running the orchestrator" today means the coordinating session reads
`.claude/agents/vulnres-orchestrator.md` directly and dispatches each stage per its logic,
rather than a single `Agent({subagent_type: "vulnres-orchestrator"})` call doing it.

## Exit gate for the whole suite

- `01` runs as a CI check and is green (or has tracked, non-blocking findings) on the
  current `main`.
- `02`+`03` have been run at least once end-to-end in an approved sandbox, producing at
  least a smoke-test-clean result (crash or no crash — either is a valid first run).
- If any crash was found: `04` and `05` have produced at least one complete
  finding-to-resolution cycle, proving the handoff contract works, not just that each
  stage works in isolation.
