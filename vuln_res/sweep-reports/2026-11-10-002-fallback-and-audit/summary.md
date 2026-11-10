---
sweep_id: 2026-11-10-002-fallback-and-audit
date: 2026-11-10
agents_run: [vulnres-recon (run directly by the coordinating session, via the fallback documented in ../../plans/06-orchestration-and-scheduling.md — not a native subagent_type call)]
environments_used: []
duration: well under an hour, static analysis + one approved host-level install, no sandbox needed
---

## What this sweep did and why

Direct follow-up to `2026-11-10-001-recon-verification`, closing out its two open items
and root-causing its operational finding instead of leaving it as "needs a fresh
session to confirm":

1. Re-tested `Agent({subagent_type: "vulnres-recon"})` in a genuinely fresh session
   (post-`/clear`, with the `.claude/agents/vulnres-*.md` files now committed to git,
   not just present on disk as untracked files like the first test). **Same failure.**
   This rules out "just needs a session restart" and prompted actually diffing the
   Agent tool's available-agents list against `ls ~/.claude/agents/` — which matched
   exactly. **Root cause: this harness only loads subagent types from the global
   `~/.claude/agents/` directory; project-level `.claude/agents/` is never scanned, in
   any project in this monorepo** (confirmed also true for `sensai-stack`,
   `parit-architecture`, `compilar-v0.5`'s own unused project-level agent folders).
   Filed as harness feedback via `/feedback`. Documented the fallback invocation
   pattern (dispatch a `general-purpose` agent with a prompt naming the exact
   `.claude/agents/vulnres-<stage>.md` path) in `plans/06-orchestration-and-scheduling.md`
   and `plans/README.md`, so the suite is actually usable today rather than blocked on
   an upstream fix.
2. User approved installing `cargo-audit`/`cargo-deny` (previously deferred,
   `cargo-audit-cargo-deny-not-installed.md`). Installed via `cargo install`, then ran
   `cargo audit` for real against this repo's `Cargo.lock`.
3. Re-ran the `.contains()` lint from plan `01` across the full `src/` tree, now against
   the *patched* code (sweep 001's `parse_ssv_enabled` fix is committed) — checking
   whether any additional security-relevant `.contains()` call lacks a fail-closed
   branch, beyond the three already known (two cited in `AUDIT.md` §2, one found and
   fixed in sweep 001).

## Commands actually run

```
$ cargo install cargo-audit cargo-deny
   Installed package `cargo-audit v0.21.2` ...
   Installed package `cargo-deny v0.20.2` ...
   Summary Successfully installed cargo-audit, cargo-deny!

$ cargo audit
    Fetching advisory database from `https://github.com/RustSec/advisory-db.git`
      Loaded 1439 security advisories (from /Users/nullzero/.cargo/advisory-db)
    Updating crates.io index
    Scanning Cargo.lock for vulnerabilities (66 crate dependencies)
EXIT:0   # zero vulnerabilities found

$ grep -n '\.contains(' src/*.rs src/state/*.rs
src/env.rs:72        — `os_type_line.to_lowercase().contains("one true recoveryos")`
                        — has an explicit `else => Err(UnconfirmedRecoveryVariant)` branch;
                        `is_mutation_allowed()` only returns `true` on the `Ok(OneTrueRecovery)`
                        match — confirmed fail-closed, matches AUDIT.md §2's original note.
src/state/collect.rs:224-230 — `parse_security_mode`'s full/permissive/reduced chain
                        — has an explicit `else => SecurityMode::Unknown` branch — confirmed
                        fail-closed, matches AUDIT.md §2's original note.
src/state/collect.rs:210 — `parse_ssv_enabled` (sweep 001's fix) — explicit `None` on an
                        unrecognised value; caller treats `None` as `CollectError`, not a guess —
                        confirmed fail-closed.
(all other .contains() call sites: test assertions or non-security-relevant string matches,
 e.g. plan.rs's own test code, diff.rs's path-string assertions — not gating a mutation or
 trust decision)
```

**Result: no new unguarded `.contains()` instance found.** The three security-relevant
call sites in this codebase today all fail closed on an unrecognised value. This is a
clean re-pass, not a re-citation — each site's actual branching logic was read, not
assumed from the doc comment above it.

## Findings produced

None new. (This sweep closed/root-caused the existing
`agent-registry-not-live-this-session` finding rather than opening a new one — see that
file's updated "Root cause" section.)

## Knowledge entries written or updated

- [`cargo-audit-cargo-deny-not-installed`](../../knowledge/cargo-audit-cargo-deny-not-installed.md) —
  updated from "deferred, not installed" to "installed, scan clean (0 vulns / 66 crates)".

## Blocked on / escalated to human

- The subagent-registry gap itself is a harness issue outside this repo's control —
  feedback filed, fallback invocation path documented and now the suite's actual
  invocation method until/unless upstream fixes it. Nothing further to do here unless a
  future session reports the native `subagent_type` path now resolves.
