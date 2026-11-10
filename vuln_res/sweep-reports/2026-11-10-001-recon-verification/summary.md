---
sweep_id: 2026-11-10-001-recon-verification
date: 2026-11-10
agents_run: [vulnres-recon (run manually by the coordinating session — see note below)]
environments_used: []
duration: a few minutes, static analysis only, no sandbox needed
---

## What this sweep did and why

A verification sweep, requested directly: confirm the `vuln_res/` suite actually works
end to end and is genuinely thorough ("aggressive"), not just a set of plans that sound
right. `vulnres-recon`'s own agent type (`.claude/agents/vulnres-recon.md`) was invoked
via the Agent tool first; the harness returned `Agent type 'vulnres-recon' not found` —
newly-added project-level `.claude/agents/*.md` files aren't picked up by the running
session's agent registry without a fresh session. That's recorded here as a real,
load-bearing finding about the suite's current operational state (see
`agent-registry-not-live-this-session.md`), not glossed over. The coordinating session
then ran the exact same recon procedure directly, to verify the plan's logic is sound and
produce real output — this sweep's results are genuine, not simulated.

## Commands actually run

```
$ cargo build
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.42s

$ cargo test
running 44 tests
test result: ok. 44 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.43s

$ cargo clippy --all-targets -- -D warnings
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.45s
(exit 0, zero warnings)

$ cargo fmt --check
(exit 0, no diff)

$ ./scripts/ci_guards.sh
== Guard 1: Command::new / std::process::Command only inside src/wrapper.rs ==
OK
== Guard 2: no credential-shaped field anywhere ==
OK
(exit 0)

$ grep -rniE '(password|passwd|credential|secret|owner_pin|recovery_key)' src/ --include='*.rs'
src/plan.rs:43,123,255,309,313 — owner_credentials: bool  (reviewed, see knowledge entry)

$ grep -rn 'Command::' src/ --include='*.rs'
src/wrapper.rs:45  Command::new(argv0)          — the one legitimate process spawn
src/main.rs:95-102  Command::Evaluate / Plan / Report / Verify / Apply / Revert
                     — clap's own Subcommand enum, name collides textually with
                     std::process::Command but isn't it (see knowledge entry)

$ grep -n '\.contains(' src/*.rs src/state/*.rs
(13 call sites found; see the finding below for the one AUDIT.md missed)
```

## Findings produced

- [ssv-enabled-contains-whole-blob.md](./ssv-enabled-contains-whole-blob.md) — a third,
  previously-undocumented instance of `AUDIT.md` §2's brittle-parsing pattern, and the
  highest-scored static finding in this suite so far (score 9: reachable from every CLI
  subcommand, feeds a security-relevant field, no fail-closed branch at all unlike the two
  already-documented instances).
- [agent-registry-not-live-this-session.md](./agent-registry-not-live-this-session.md) —
  an operational finding about the suite itself: the newly-created `.claude/agents/`
  files aren't in this session's agent registry yet.

## Knowledge entries written or updated

- [`build-test-clippy-fmt-clean-2026-11-10`](../../knowledge/build-test-clippy-fmt-clean-2026-11-10.md)
- [`owner-credentials-field-reviewed-cleared`](../../knowledge/owner-credentials-field-reviewed-cleared.md)
- [`command-enum-name-collision-tool-note`](../../knowledge/command-enum-name-collision-tool-note.md)
- [`cargo-audit-cargo-deny-not-installed`](../../knowledge/cargo-audit-cargo-deny-not-installed.md)

## Blocked on / escalated to human

- `cargo audit`/`cargo deny` remain uninstalled — installing them needs explicit
  host-level go-ahead, not assumed here (see the knowledge entry).
- The agent-registry gap above means `vulnres-orchestrator`/the other six stage agents
  are still unverified as *invokable subagents* in a live session — their logic has been
  manually walked through and matches what actually happened in this sweep, but that's
  not the same as having run one of them as an actual Agent-tool call. Confirming that
  needs a fresh Claude Code session in this repo (or project directory) — worth checking
  next time one starts here.
