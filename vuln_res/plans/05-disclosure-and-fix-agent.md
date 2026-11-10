# 05 — Disclosure and fix agent

Consumes the scored findings from `04` and produces, for each one, exactly one of two
outcomes — never a working exploit:

## Case A — the bug is in our own code (expected case, for everything this suite targets)

This is the normal case, since every target in `02` is `bputil-eval`'s own source. Output:

1. A minimal, reviewable patch (e.g. a size/depth guard before `serde_json::from_str` for
   the `cmd_verify` finding, or a bounds/length sanity check before `image4`'s decode for
   the `img4.rs` finding).
2. A regression test built directly from the minimized PoC fixture from `04` —
   `#[test] fn does_not_<panic/hang/overflow>_on_<description>() { ... }`, using
   `include_bytes!` on the committed fixture, same pattern this codebase already uses for
   its own fixture-driven tests (`state/img4.rs`'s `tests` module is the template).
3. A short writeup (what, why, how it was found, how it's fixed) suitable as a commit
   message body, following this repo's existing commit-message conventions
   (`[PROJ-123] type: description`, per the root `../../CLAUDE.md`'s "Git Workflow"
   section — use `MP-###` for this since it's Metacogna-platform tooling, or ask the user
   which Linear prefix applies to `vuln_res/` work specifically).

Fixes land as an ordinary PR through this repo's normal review process — nothing about
"this came from a fuzzer" changes that a human reviews the diff before it merges.

## Case B — the bug reveals something about an upstream dependency (`image4`, `der`,
`serde_json`) rather than this repo's own glue code

Standard open-source practice, not this project's invention:
1. Confirm the minimized crash reproduces against the dependency in isolation (a tiny
   standalone `fn main()` calling just the library function, no `bputil-eval` code
   involved) — proves it's the library's bug, not a misuse of its API.
2. File an issue (or, if comfortable, a PR) upstream with the minimized PoC, following
   that project's own disclosure norms. Most pure-Rust parsing crates don't have a formal
   security-disclosure process (check `SECURITY.md` in the upstream repo first; use it if
   present), so a public issue with a minimized, non-sensitive input is normal practice
   here — this is not the SEP/iBoot "coordinated disclosure to Apple" case the root
   `CLAUDE.md` describes; it's routine open-source bug reporting.
3. Pin `Cargo.lock` to a known-safe version (or add a guard in our own glue code) in the
   meantime so the fix lands in `bputil-eval` regardless of upstream's timeline.

## Case C — the "finding" is actually about Apple's platform security

This should not happen if `00`'s scope is respected (none of this suite's targets touch
Apple's firmware as an attack surface), but if an agent in this pipeline ever produces
something that looks like it — stop, don't draft a PoC or a writeup, and surface it to the
user directly per the root `CLAUDE.md`'s "Invariant violations are findings, not
retryable errors" / coordinated-disclosure stance. This case gets a person, not an agent,
deciding what happens next.

## What this agent never produces

- A working exploit chain.
- A disclosure document aimed at anyone other than this project's own maintainers or (in
  Case B) an upstream crate's own issue tracker.
- A patch that "fixes" a finding by suppressing the symptom (e.g. catching a panic and
  ignoring it) rather than addressing the actual unsafe/unvalidated input path — same
  "fix the root cause" standard the top-level system instructions already hold all work
  in this repo to.

## Exit gate

For every finding handed off from `04`: either a merged (or PR-ready) fix with a
regression test, an upstream issue filed with a minimized reproducer, or an explicit
human escalation — never a finding left as just a markdown file with no next action taken.
