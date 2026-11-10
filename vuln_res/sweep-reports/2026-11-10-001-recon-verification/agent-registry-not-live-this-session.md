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

Open. Next step: the next Claude Code session started in this repo (or with this
project's `.claude/agents/` on its path) should try `Agent({ subagent_type:
"vulnres-recon" })` again and confirm whether it now resolves. If it does, close this
and note the fix (session restart) in `knowledge/`. If it still doesn't, that's worth
raising as a question about this harness's `.claude/agents/` discovery mechanism, not
something to keep working around by running procedures manually.
