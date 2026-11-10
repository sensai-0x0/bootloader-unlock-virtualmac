---
id: 2026-11-10-001-recon-verification/agent-registry-not-live-this-session
target: .claude/agents/vulnres-*.md (operational, not a code vulnerability)
source: static-analysis
status: open
score: n/a — operational/tooling gap, not a security finding
discovered_by: coordinating session (direct Agent tool call)
sweep: ../INDEX.md#2026-11-10-001-recon-verification
discovered_at: 2026-11-10
---

## Short description

The seven `vulnres-*` subagents built into this repo's `.claude/agents/` folder aren't
recognized yet by this running session — trying to invoke `vulnres-recon` through the
Agent tool returned `Agent type 'vulnres-recon' not found`. This isn't a vulnerability;
it's a gap between "the suite's logic is correct" (confirmed — this sweep's actual
results prove the recon procedure works) and "the suite is invokable as designed" (not
yet confirmed in a live session).

## Technical detail

Calling the Agent tool with `subagent_type: "vulnres-recon"` returned:

```
Agent type 'vulnres-recon' not found. Available agents: api-contract-validator,
bohemian-design-expert, claude, claude-code-guide, documentation-architect,
error-analyzer-resolver, Explore, frontend-design-auditor, general-purpose,
integration-production-specialist, Plan, statusline-setup
```

— the same list present at session start, before any `vulnres-*` file existed.
Project-level `.claude/agents/*.md` additions most likely require a fresh session (or
whatever mechanism this harness uses to refresh its agent registry) to become callable;
they don't appear to be picked up mid-session.

**What was done instead, to still verify the suite's actual logic:** the coordinating
session ran `vulnres-recon`'s exact procedure directly — `cargo build`, `cargo test`,
`cargo clippy --all-targets -- -D warnings`, `cargo fmt --check`, `./scripts/ci_guards.sh`,
and the independent greps for credential fields, `Command::` usage, and `.contains()`
call sites — and that run is what produced
[`ssv-enabled-contains-whole-blob.md`](./ssv-enabled-contains-whole-blob.md). The
*procedure* is verified and genuinely found something real. The *agent* as an invokable
subagent is not yet confirmed.

## Reproduction

```
Agent({ subagent_type: "vulnres-recon", ... })
=> Agent type 'vulnres-recon' not found. Available agents: [...]
```

## Classification

Not a `memory-safety | panic | hang | logic-divergence` classification — this is an
operational/infrastructure gap in the suite's own invocability, tracked here because
`sweep-reports/` is the right place to record "did the thing actually run," not just
"what security bug did it find."

## Resolution

Still open — re-tested 2026-11-10 in a genuinely fresh session (after `/clear`, with the
`.claude/agents/vulnres-*.md` files now committed to the repo, not just present on disk
as untracked files as they were during the first test). Same result:

```
Agent({ subagent_type: "vulnres-recon", ... })
=> Agent type 'vulnres-recon' not found. Available agents: api-contract-validator,
bohemian-design-expert, claude, claude-code-guide, documentation-architect,
error-analyzer-resolver, Explore, frontend-design-auditor, general-purpose,
integration-production-specialist, Plan, statusline-setup
```

This rules out "just needs a session restart" as the fix — a fresh session with the
files committed still doesn't see them. The seven `vulnres-*` agent definitions in
`.claude/agents/` are not being picked up by this harness's project-level agent
discovery at all, in this environment, across two independent sessions. Worth raising
directly with the user as a possible product/harness question (e.g. via `SendFeedback`)
rather than continuing to assume a third retry will differ. Until resolved, every
`vulnres-*` "agent" in this suite remains usable only as a **procedure document** that a
general-purpose session or subagent reads and follows manually, not as an invokable
`subagent_type`.

**User confirmation (2026-11-10):** project-level `.claude/agents/*.md` files are meant
to be scoped to the project they live in — discoverable when a session is working inside
that project's directory, not globally across unrelated repos. That's the expected
design, and it's exactly what's failing here: this session *is* running inside
`the-ant-experiment` (the same repo the `vulnres-*` files live in), yet they still don't
appear in the available-agents list. So the gap isn't "these are global agents that
should've been filtered out" — it's "these are correctly-scoped project agents that
aren't being discovered at all." Feedback already filed via `/feedback` on 2026-11-10;
no further action pending here unless the user reports it's fixed in a later session.

**Root cause, confirmed 2026-11-10:** the harness's Agent tool only loads subagent types
from the **global, user-level** `~/.claude/agents/` directory. `ls ~/.claude/agents/`
returns exactly `api-contract-validator.md`, `bohemian-design-expert.md`,
`documentation-architect.md`, `error-analyzer-resolver.md`,
`frontend-design-auditor.md`, `integration-production-specialist.md` — a one-to-one
match with the Agent tool's "Available agents" error list (minus the harness's own
always-present built-ins: `claude`, `claude-code-guide`, `Explore`, `general-purpose`,
`Plan`, `statusline-setup`). Project-level `.claude/agents/*.md` is never scanned at all
in this environment: besides this repo's seven `vulnres-*` files, three sibling projects
in the same monorepo (`sensai-stack/.claude/agents/`, `parit-architecture/.claude/agents/`,
`compilar-v0.5/.claude/agents/`) have their own project-level agent definitions that are
equally invisible to the Agent tool, regardless of which project's directory a session
is working in. So this isn't specific to `the-ant-experiment` or to `vulnres-*` — it's a
general project-level-agent-discovery gap in this harness build.

**Practical workaround adopted (not a fix):** `vulnres-*` agents are invoked via a
`general-purpose` subagent given a prompt that names the exact `.claude/agents/<name>.md`
path and tells it to read and follow that file — see
`../../plans/06-orchestration-and-scheduling.md`'s "How to actually invoke this suite
today" section. This keeps the agent definitions themselves correctly project-scoped
(they live only in this repo, never copied into the global directory to work around the
bug) while still making them actually usable from `vuln_res/`'s pipeline today.
