# Execution Product Report — `bputil-eval`

**Report date:** 2026-11-10
**Scope:** What running the built binary actually produces today, on real hardware, versus what remains unimplemented.

This report describes the *execution* behavior of the binary documented in `reports/build-product.md` — the CLI surface, exit codes, and evidence it generates — and draws the line precisely between what has been verified by a fresh measurement on real hardware and what is specified but not yet implemented.

## 1. CLI surface

```
cargo run -- evaluate [--json]                                  # read-only
cargo run -- plan <full|reduced-kexts|permissive-custom-kernel> [--json]
cargo run -- verify --baseline <path-to-evaluate---json-output> [--json]
cargo run -- report [--out-dir <dir>] [--session-id <id>]
cargo run -- apply    # prints "not implemented (P3/P4)" and exits non-zero, on purpose
cargo run -- revert   # same
```

`evaluate`, `plan`, `verify`, and `report` never mutate anything on the host — this is enforced by the `ci_guards.sh` subprocess-isolation check described in `reports/build-product.md` §4, not just asserted in documentation.

## 2. Verified, concretely, on real hardware (this session's host, an Apple M2 Pro)

- `cargo build`, `cargo test` (44 tests), `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check`, and `./scripts/ci_guards.sh` all pass.
- `cargo run -- evaluate --json` run twice on this real Mac differs **only** in `captured_at` — the literal P1 exit-gate proof from `spec/phased-plan.md`, reverified after the `evidence.raw_outputs` scoping fix (`reports/build-product.md` §5).
- `cargo run -- plan full` on this machine correctly refuses with exit code 11 ("current security_mode is Unknown") because there is no cached `sudo` credential to read the real policy. This is the fail-closed path working as designed, not a defect: without a privileged read, the tool reports its own uncertainty rather than guessing.

## 3. Evidence model

`report` produces a hash-chained bundle: `report.json` plus `report.sha256`. Golden rule 8 ("never claim a state change succeeded without a fresh `BootState` measurement proving it") is structural here, not aspirational — `verify` takes a `--baseline` argument that must itself be prior `evaluate --json` output, so a claimed transition is always checked against a real prior measurement, never an assumption.

Within `evidence.raw_outputs`, only security-relevant command outputs are hashed (`csrutil authenticated-root status`, `bputil -d`). Host-identification reads (`diskutil info /`, `diskutil apfs listVolumeGroups`, `ioreg -c IOPlatformExpertDevice`) still pass through the audited `wrapper` — so the no-direct-subprocess guard still holds for them — but are excluded from the hashed evidence set because they contain live, constantly-changing counters (free space, per-volume capacity, an uptime-derived figure) that would make two consecutive `evaluate` runs differ in more than just a timestamp.

## 4. What `apply`/`revert` do today

They print a "not implemented (P3/P4)" message and exit non-zero — on purpose. This is the one place in the CLI surface where "not implemented" is itself the correct, verified behavior: it proves no mutating code path exists yet, which is exactly what the P2→P3 gate in `spec/phased-plan.md` requires before any mutation logic is written.

## 5. What is specified but not executed

Per `reports/build-product.md` §6, the entire mutation pipeline — `authorize` (human-gated confirmation), `execute` (running the planned `bputil`/`kmutil`/`csrutil` invocations), and `verify`'s mutating-aware half, plus the Permissive/custom-kernel path and `revert` — has no logic behind it. Concretely, that means:

- No `full → reduced-kexts → full` round trip has ever been executed by this tool, on any target, real or virtual.
- No `apply` outside 1TR → exit 10 negative test has run, because there is no `apply` logic to test.
- No executor-rejects-an-argv-not-in-the-plan test has run, for the same reason.
- No wrong-post-state → exit 13 test has run.

These are the P3 exit-gate tests from `spec/phased-plan.md`, and they remain unexecuted by design — see §6.

## 6. Why the mutation half is unexecuted, not just unfinished

`spec/phased-plan.md`'s P3 exit gate requires a disposable APFS scratch container and a human physically rebooting into One True Recovery to enter owner credentials — neither of which this agent can do unattended in a terminal session. Implementing `authorize`/`execute`/`verify`'s logic without a way to prove it against a real round trip would mean shipping untested, safety-critical code against a boot-security surface, which `spec/build-spec.md`'s golden rules treat as strictly worse than not shipping it at all.

An active research track (see `reports/disposable-vm.md` and `reports/unlocked-bootloader-evidence.md`) is exploring whether a disposable virtual machine — rather than real scratch hardware — can serve as that target, so the P3 round trip can be proven without physical-device risk. As of this report, that question is still open: a VM has not yet been successfully booted on this host (see the companion reports for why), so no execution evidence exists yet for the mutating half of the tool on *any* target.

## 7. Summary

Everything the binary currently executes is read-only and verified by fresh, repeatable measurement on real hardware. Nothing it specifies as a mutation has ever actually run. That boundary is intentional, tooling-enforced, and the single most load-bearing fact about this project's current state: the read-only evaluator is a finished, trustworthy product; the owner-authorized unlock pipeline is a fully specified but entirely unexecuted design, waiting on a safe, disposable target to prove itself against.
