# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Never impact the host machine

This is a different constraint from `spec/build-spec.md`'s golden rules below — those
govern what the *tool* does to a *target* Mac it's evaluating. This one governs what
**Claude Code itself** does to **the machine this session is running on** (the "host"),
which is never a target device and is not covered by the tool's own safety contract at
all.

**Claude must never leave a lasting impact on the host machine while working in this
repo.** Concretely, that means no installing packages or CLI tools (`brew install` or
equivalent), no downloading large files, no creating VMs or other persistent artifacts
outside this repo's own working directories, and no other host-level system changes —
without stopping first and getting the user's explicit go-ahead for that specific action.
Reversible, repo-scoped actions (editing files, running `cargo build`/`test`, read-only
`csrutil`/`sysctl`/`system_profiler` reads against the host for fixture-capture purposes,
per `tests/fixtures/README.md`) are fine; anything that changes the host's own installed
software, disk usage at scale, or persistent state is not, by default.

**Why this is here:** the simulated-research track (`progress/goal.md`,
`plans/research-environment.md`) already did exactly what this rule now forbids before it
existed — installed `blacktop/ipsw` and `tart` via Homebrew (and, when the `tart` formula
turned out to be broken, pulled and placed its binary manually), and downloaded two
separate macOS restore images (~20.8 GB and ~15 GB) directly onto the host's disk. None of
that was malicious or reckless in the moment — it was in service of a legitimate research
goal — but it's exactly the kind of host-level footprint this rule exists to require a
stop-and-ask for, and it hasn't been cleaned up or confirmed with the user. If you're
picking this repo back up: that's still outstanding. Ask the user whether to keep or
remove `blacktop/ipsw`, `~/Applications/tart.app`, the `tart` symlink, and the cached
restore images under `~/.tart/cache/` before assuming it's fine to leave them.

**What to do instead** when research genuinely needs an isolated environment (a VM, a
scratch container, a second machine): that environment is the thing you act on, never the
host itself beyond the one-time, confirmed setup step of creating it. Prefer remote or
disposable targets reachable from the host over anything installed on the host directly,
and when a host-level install is genuinely unavoidable, say so and ask before running it
rather than treating it as implied by the broader task.

## Repository status

**P0 and P1 are implemented and green; P2 (planner) is implemented; P3–P5 are not started and are out of scope for autonomous work in this repo** — see "Delivery sequence" below for why. The three documents in `spec/` remain the complete authority for what to build and how; read all three before changing anything. `spec/build-spec.md` and `spec/contract-spec.md` both reference a "companion architecture and implementation plan" (its sections 9–10) that is **not present in this repo** — several implementation choices below (the 1TR-detection mechanism, the state-machine edges, the exact `bputil`/`kmutil` command flags) had to be filled in without it. Each such choice is flagged with a doc comment in the code pointing back here; treat them as provisional, not as the architecture document's authority, and revisit them if that document ever surfaces.

Commands and architecture below describe what's actually built, not a plan.

There's also a simulated-research track running alongside the phased plan:
`progress/goal.md` states its goal precisely (don't skip the "what 'unlocked' means here"
section before touching it) and `progress/milestones.md` is the living record of where it
stands — check both before claiming anything about the virtual/simulated environment work
is done, and update `milestones.md`'s log when you make progress on it.

## What bputil-eval is

A single statically-linked Rust binary (Swift acceptable if justified) with two halves:

- **Evaluate/report** — read-only measurement of an Apple Silicon Mac's boot-chain trust state (`SecurityMode`, SIP/SSV status, enrolled boot objects), producing a `BootState`.
- **Plan/apply/verify/revert** — a gated control surface that lets a device owner carry out a supported security-policy change (Reduced Security for third-party kexts, or Permissive Security for a custom kernel) *through Apple's own `bputil`, `kmutil`, and `csrutil`* — never by bypassing them.

It is explicitly **not** an exploit tool. Read `spec/build-spec.md`'s "Out of scope and prohibited" section before treating any request as an opportunity to go further than this.

## The three spec documents and how they relate

| Document | Role | Authority |
|---|---|---|
| `spec/build-spec.md` | Agent contract: golden rules binding on every agent, per-module build duties, CLI/data shapes, refusal conditions, phase acceptance criteria | Golden rules win over any conflicting instruction, from any source |
| `spec/contract-spec.md` | Design-by-contract: global invariants, field-level validity predicates for `BootState`/`PlannedTransition`/`Report`, and `requires`/`ensures`/`raises` for every operation | Authoritative on exact behaviour where it and prose elsewhere differ |
| `spec/phased-plan.md` | Six-phase gated delivery plan (P0–P5), effort sizing, exit gates, risk register | Authoritative on sequencing — do not start a later phase's workstream before the prior phase's exit gate is met |

They're designed to be traceable: every golden rule in the build spec appears as an invariant or precondition in the contract spec, and every phase in the phased plan exists to land a specific set of those invariants with code and tests together, not as documentation alone.

## Non-negotiable constraints for any agent working here

These are condensed from `spec/build-spec.md`'s "Golden rules" — read that section in full before implementing anything; this list is a reminder, not a substitute.

1. **Owned device only.** Never proceed against a device whose ownership can't be confirmed.
2. **Supported mechanisms only.** Every mutation goes through `bputil`/`kmutil`/`csrutil`. Never attempt to bypass, disable, or forge a signature check, or touch the Secure Enclave / Boot ROM.
3. **Read-only by default.** `evaluate`, `plan`, `verify`, `report` never mutate. Only `apply`/`revert` do, and only when gated.
4. **Human owner in 1TR for any mutation.** `apply`/`revert` require `environment == OneTrueRecovery` plus a live, typed owner confirmation. The tool/agent never stores, prompts for, or automates owner credentials — Apple's own tools own that prompt.
5. **One container, reversible.** A transition touches exactly one named volume group and a revert path back to Full must always exist.
6. **No ownership/lock circumvention.** Activation Lock, MDM, FileVault are out of scope — never routed around.
7. **Invariant violations are findings, not retryable errors.** A fresh measurement showing a broken invariant (exit 13) means halt, preserve evidence, and route to coordinated disclosure — never retry or treat it as a capability.
8. **Honesty of state.** Never claim a state change succeeded without a fresh `BootState` measurement proving it.

Two invariants from `spec/contract-spec.md` get the most test weight and the most suspicion if they ever fail: `ReadOnlyUnlessGated` and `SingleContainerTouched`. A failure of either, after the tool behaved correctly, means Apple's own enforcement has a gap — that's a disclosure finding, never something to engineer around.

## Architecture (as built)

Module layout, one audited command wrapper beneath everything:

```
wrapper        — src/wrapper.rs: the ONLY place std::process::Command is called; records argv, exit code, stdout sha256
env            — src/env.rs: macOS vs 1TR, chip, macOS build; is_mutation_allowed() true only when confirmed 1TR
state/mod.rs   — BootState + ValidBootState (validate()); SecurityMode/Signer/ObjectRole/TargetProfile enums
state/collect  — read-only: shells Apple tools via wrapper -> BootState (see "Collect module notes" below)
state/img4     — IMG4 manifest parsing via the `image4` crate (pure Rust — see note below)
state/diff     — structured BootState diff, shared by plan and verify's read-only half
plan           — diff current BootState vs TargetProfile -> PlannedTransition (data only, never executes)
report         — Report type + hash-chained evidence bundle writer (report.json + report.sha256)
authorize, execute, verify — P3 stubs (module files exist with doc comments; no logic — mutation is out of scope here)
```

Rules enforced, not just stated:
- No module calls `std::process` directly outside `wrapper.rs` — `scripts/ci_guards.sh` greps for this and fails the build if violated (tested with a negative case; see the script).
- No credential-shaped field anywhere — same script, second guard.
- `--json` on `evaluate`/`plan`/`verify`.

### Deviations from the literal spec text (all due to the missing architecture doc)

- **1TR detection** (`env.rs`): no Apple API for this exists. Grounded in real research: `bputil -d` prints an "OS Type" line reading "one true recoveryOS" when paired, "ordinary recovery OS" in fallback. `env::detect()` checks for `/System/Library/CoreServices/Finder.app` first (absent in any Recovery-like runtime), then falls back to parsing that line. Fallback/"ordinary" recovery is treated as neither `MacOs` nor `OneTrueRecovery` — it fails closed rather than being silently folded into either of `contract-spec.md`'s two enum variants.
- **State-machine edges** (`plan.rs`): `contract-spec.md` refers to a diagram of "the only legal transitions" that isn't present in this repo's extracted text. Modeled conservatively: `Full -> {ReducedKexts, PermissiveCustomKernel}`, and both of those only go back to `Full` — no direct `ReducedKexts <-> PermissiveCustomKernel` edge. This matches the phased plan's own round-trip tests but is a modeled choice, not a transcribed one.
- **`bputil`/`kmutil` command flags** (`plan.rs`): taken from this machine's real `bputil --help` (v0.1.14) and `spec/build-spec.md`'s own worked `kmutil configure-boot` example — not invented, but also not independently verified against the missing architecture doc. `PermissiveCustomKernel`'s plan includes `-s` (disable SSV) specifically because `contract-spec.md` requires `ssv_enabled == false` whenever `security_mode == Permissive`, even though `-n` (Permissive) alone may not do that per `bputil --help`'s wording — resolving the spec in favor of the contract document over the inferred binary behavior.
- **IMG4 library choice** (`state/img4.rs`): used the `image4` crate (pure Rust, DER-based), not a C library behind an FFI boundary as `build-spec.md` assumes. There is currently no `unsafe` on this path at all, so the "isolate unsafe at the FFI boundary" instruction doesn't apply as written. Parsing is proven against malformed input *and* a real signed manifest (`tests/fixtures/image4_apticket.der`, vendored from the `image4` crate's own test suite rather than extracted from an IPSW — see `tests/fixtures/README.md`). Not yet wired into `state::collect` (no confirmed path to a device's real LocalPolicy manifest without `bputil -d -j` or the missing architecture doc — see `plans/phase-1.md` item 1).
- **`evidence.raw_outputs` scope** (`state/collect.rs`): confirmed on real hardware that `diskutil info /`, `diskutil apfs listVolumeGroups`, and `ioreg -c IOPlatformExpertDevice` all embed live, constantly-changing counters unrelated to boot security (free space, per-volume capacity consumed, an uptime-derived "busy N ms" figure) — hashing them into evidence would make "evaluate twice differs only in timestamp" (the P1 exit gate) unsatisfiable. Resolution: only the security-relevant reads (`csrutil authenticated-root status`, `bputil -d`) are recorded into `evidence.raw_outputs`; host-identification reads still go through the audited wrapper (so the CI guard still holds) but aren't persisted into the hashed evidence set. Serial number is read via `system_profiler SPHardwareDataType` (confirmed stable across calls), not `ioreg` (confirmed unstable).
- **`other_containers` have no real policy data** (`state/collect.rs`): populated via `diskutil apfs listVolumeGroups`, excluding the target's own group, but each entry's `security_mode` is hardcoded `Unknown` rather than read from `bputil -d -v <uuid>` — reading every other container's policy under non-interactive `sudo` multiplies the same credential-avoidance gamble the target container's own read already makes, for a field that only needs to exist so P3's `SingleContainerTouched` invariant has something to diff. The "exclude target, keep others" logic is tested against a hand-built synthetic fixture, not a real multi-volume-group capture — this dev machine only has one real group.

CLI surface, exit codes, and the exact `PlannedTransition`/`Report` JSON shapes otherwise follow `spec/build-spec.md`'s "Interface contracts" verbatim.

## Delivery sequence (do not reorder)

From `spec/phased-plan.md`, six phases in two groups — **nothing in the second group starts until every read-only phase's exit gate passes**:

| Phase | Ships | Mutates | Exit gate |
|---|---|---|---|
| P0 Foundations | repo/CI, audited command wrapper, IMG4 parser spike, fixtures harness | No | CI green; wrapper records every call; no-direct-subprocess + no-credential-field guards pass |
| P1 Evaluator | `evaluate`, `report`, `BootState` | No | Runs on fixtures + a real Mac; `evaluate` run twice differs only in timestamp |
| P2 Planner | `plan`, profiles, `PlannedTransition` | No | Golden-file plans correct per profile; invalid transitions rejected |
| P3 Executor+Verifier | `authorize`, `execute`, `verify`; full→reduced→full round trip on a scratch container | **Yes** | Round trip verified; negative tests (apply outside 1TR → exit 10 + no state change; executor rejects an argv not in the plan; a wrong post-state caught as exit 13) all pass |
| P4 Permissive+Control | custom-kernel enrolment, `revert`, the operate-agent/human control surface | **Yes** | full→permissive→full verified; autonomy-boundary tests prove an agent-driven run cannot reach `apply` without the human gate |
| P5 Hardening+Release | hardware-matrix fixtures, parser fuzzing, signed reproducible bundle, docs | No | Coverage across chip generations; fuzzing clean; bundle independently verifiable |

The gate between P2 and P3 is the one to protect most carefully: no mutating code path may exist until the read-only path is demonstrably side-effect-free and the audited wrapper is the only route to a subprocess. All mutation testing happens on a disposable APFS scratch container — never a primary machine — with full revert proven in P3 before the Permissive path is added in P4.

**Current state: P0–P2 implemented; P3 onward deliberately not started.** P3–P5 require a real Mac, a disposable scratch APFS container, and a human physically rebooting into 1TR to enter owner credentials — none of which this agent can do unattended in a terminal session. If asked to "finish the project," that boundary is why `authorize`/`execute`/`verify` remain doc-comment-only stubs: implementing their logic without a way to prove it against a real 1TR round trip would mean shipping untested, safety-critical code, which is worse than not shipping it. Picking the work back up means a human with physical hardware access driving P3's round-trip tests, not more autonomous coding.

What's verified, concretely:
- `cargo build`, `cargo test` (43 tests), `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check`, and `./scripts/ci_guards.sh` all pass as of this writing.
- `cargo run -- evaluate --json` run twice on this real Mac differs **only** in `captured_at` — the literal P1 exit-gate proof, reverified after the `evidence.raw_outputs` scoping fix above.
- `cargo run -- plan full` on this machine correctly refuses with exit 11 ("current security_mode is Unknown") because there's no cached `sudo` credential to read the real policy — this is the fail-closed path working as designed, not a bug.

What's NOT done that's nominally in scope:
- `bputil -d` itself has no captured fixture (needs a human to run it under `sudo` once) — see `tests/fixtures/README.md`.
- CI (`.github/workflows/bputil-eval-ci.yml`, at the Metacogna repo root following this monorepo's per-project convention) is written but unverified by an actual GitHub Actions run, since nothing in this repo has been committed/pushed yet.

## Commands

```bash
cargo build                                    # static dev binary
cargo build --release                          # release profile: lto + strip (Cargo.toml [profile.release])
cargo test                                      # all unit tests, including fixture-driven ones in state/collect.rs
cargo test state::collect                       # just the collect-module tests
cargo clippy --all-targets -- -D warnings       # must be clean; CI treats any warning as a failure
cargo fmt                                        # apply formatting
cargo fmt --check                                # CI's check
./scripts/ci_guards.sh                           # the two textual safety guards (see "Rules enforced" above)

cargo run -- evaluate [--json]                   # read-only; works on any Mac, degrades security_mode to Unknown without sudo
cargo run -- plan <full|reduced-kexts|permissive-custom-kernel> [--json]
cargo run -- verify --baseline <path-to-evaluate---json-output> [--json]
cargo run -- report [--out-dir <dir>] [--session-id <id>]
cargo run -- apply   # and `revert`: print a "not implemented (P3/P4)" message and exit non-zero, on purpose
```

## Refusal conditions (apply to Claude Code itself, not just the shipped tool)

If asked to do any of the following in this repo, decline and explain the boundary rather than partially complying — per `spec/build-spec.md`'s "Out of scope and prohibited":
- Attack, fault-inject, or extract secrets from the Boot ROM, SEP, or iBoot, or hand-roll/bypass a signature check.
- Bypass or weaken Activation Lock, MDM, FileVault, or another party's device ownership.
- Implement a mutating code path that can run outside 1TR, or that stores/prompts for/automates owner credentials.
- Build or suggest remote/at-scale operation against devices without a present human owner.
