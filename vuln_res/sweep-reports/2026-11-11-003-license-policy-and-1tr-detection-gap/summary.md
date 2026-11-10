# Sweep summary — 2026-11-11-003-license-policy-and-1tr-detection-gap

**Trigger:** user asked to fix the two items left open at the end of sweep 002 (the
`cargo deny` license-policy gap, and `env.rs:72`'s brittle 1TR-detection check), then
commit, push, and continue.

## What was fixed

1. **`cargo deny check`'s license-policy gap** — added `deny.toml` at the repo root with
   an explicit `[licenses] allow` list (`MIT`, `Apache-2.0`, `Unicode-3.0` — the complete
   set across this project's dependency tree, confirmed via `cargo metadata`'s own
   `license` field for every package, not guessed). `cargo deny check` now reports
   `licenses ok` instead of `licenses FAILED`. Not a vulnerability — a missing policy file;
   `advisories`/`bans`/`sources` were already passing under cargo-deny's built-in
   defaults.

## What was escalated, not fixed

2. **`env.rs:72`'s fallback 1TR-detection check** — see
   [`env-1tr-fallback-detection-confirmed-broken.md`](./env-1tr-fallback-detection-confirmed-broken.md)
   for the full writeup. Short version: `vuln_res/AUDIT.md` §2 called this *speculative*;
   checking it against this project's own real `bputil -d` captures (the
   `_VM_VIRTUALIZED` fixtures from sweep 001, one of them from an independently-confirmed
   paired-1TR environment) shows the assumed distinguishing string
   (`"one true recoveryOS"`) **never occurs** — the real "OS Type" line reads
   `"macOS (overriden)"` in every captured state, 1TR included. This means the fallback
   branch can currently never classify anything as `OneTrueRecovery` at all.

   **Deliberately not "fixed" by guessing a replacement string** — this project's
   standing discipline (every parsing fix so far) is "confirmed, not guessed," and no
   alternative distinguishing text has been confirmed. Instead: the module doc comment
   was rewritten to state the confirmed finding plainly, the matching logic was pulled
   into a pure, testable function, and a regression test was added proving the
   confirmed-gap behavior against the real fixture — annotated so a future genuine fix
   will make the test fail loudly (a signal to update it), rather than the test silently
   "passing" a gap closed by accident.

   This is a fail-closed functional gap (blocks a future P3 capability entirely), not a
   vulnerability — no misauthorization risk, just a confirmed dead end that needs real
   research (ideally: capturing what a confirmed *un*paired fallback recovery
   environment's `bputil -d` actually prints, to find a genuine distinguishing signal) to
   close, not more code written against assumptions.

## Verification

- `cargo test`: 64/64 passing (up from 63 at the start of this sweep)
- `cargo clippy --all-targets -- -D warnings`: clean
- `cargo fmt --check`: clean
- `./scripts/ci_guards.sh`: green
- `cargo deny check`: `advisories ok, bans ok, licenses ok, sources ok` (licenses was
  previously `FAILED`)

## Left open

- `AUDIT.md` §1.1 (DER fuzz harness) — still needs `cargo-fuzz`; not installed, not
  asked about this sweep since it wasn't the focus.
- The 1TR fallback-detection gap above — needs real research (ideally access to produce
  and capture a confirmed *unpaired* fallback-recovery environment to compare against),
  not a code change. Blocks P3's `authorize`/`execute` from ever succeeding until
  resolved, but fails closed in the meantime, so nothing is unsafe about leaving it open.
