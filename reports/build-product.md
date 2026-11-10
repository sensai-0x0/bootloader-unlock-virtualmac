# Build Product Report — `bputil-eval`

**Repository:** `the-ant-experiment`
**Package:** `bputil-eval` v0.1.0 (Rust, edition 2024)
**Report date:** 2026-11-10
**Status covered:** P0 (Foundations) through P2 (Planner) — implemented and green. P3–P5 are out of scope for this report; see "What is not built" below.

## 1. Purpose

`bputil-eval` is a single statically-linked Rust binary with two halves:

- **Evaluate/report** — read-only measurement of an Apple Silicon Mac's boot-chain trust state (`SecurityMode`, SIP/SSV status, enrolled boot objects), producing a `BootState`.
- **Plan/apply/verify/revert** — a gated control surface that lets a device owner carry out a security-policy change (Reduced Security for third-party kexts, or Permissive Security for a custom kernel) through this project's custom toolchain driving `bputil`, `kmutil`, and `csrutil` — never by bypassing them.

It is explicitly **not** an exploit tool. It never attempts to bypass, disable, or forge a signature check, and never touches the Secure Enclave or Boot ROM directly. These constraints are enforced in the codebase, not just stated in documentation — see §4.

The authoritative specifications are `spec/build-spec.md` (agent contract and golden rules), `spec/contract-spec.md` (design-by-contract invariants), and `spec/phased-plan.md` (six-phase delivery sequence). A "companion architecture and implementation plan" both specs reference (their §§9–10) is **not present in this repository**; several implementation choices below had to be filled in without it and are flagged accordingly.

## 2. Module layout

One audited command wrapper sits beneath every other module:

| Module | File | Lines | Role |
|---|---|---|---|
| `wrapper` | `src/wrapper.rs` | 98 | The **only** place `std::process::Command` is called. Records argv, exit code, and a SHA-256 of stdout for every invocation. |
| `env` | `src/env.rs` | 136 | Distinguishes ordinary macOS from One True Recovery (1TR); reads chip and macOS build; `is_mutation_allowed()` returns `true` only when 1TR is confirmed. |
| `state/mod.rs` | `src/state/mod.rs` | 302 | `BootState` + `ValidBootState` (the `validate()` gate); `SecurityMode`, `Signer`, `ObjectRole`, `TargetProfile` enums. |
| `state/collect` | `src/state/collect.rs` | 316 | Read-only: shells out via the custom toolchain's `wrapper` and assembles a `BootState`. |
| `state/img4` | `src/state/img4.rs` | 91 | IMG4 manifest parsing via the `image4` crate (pure Rust, DER-based). |
| `state/diff` | `src/state/diff.rs` | 115 | Structured `BootState` diff, shared by `plan` and `verify`'s read-only half. |
| `plan` | `src/plan.rs` | 367 | Diffs the current `BootState` against a `TargetProfile` to produce a `PlannedTransition` (data only — never executes anything). |
| `report` | `src/report.rs` | 153 | `Report` type and a hash-chained evidence-bundle writer (`report.json` + `report.sha256`). |
| `authorize`, `execute`, `verify` | `src/authorize.rs`, `src/execute.rs`, `src/verify.rs` | 8, 6, 9 | **P3 stubs.** Doc-comment-only; no mutation logic exists yet (see §5). |
| `main` | `src/main.rs` | 252 | CLI entry point (`clap`-derived), command dispatch, exit codes. |

Total: **2,882 lines** across 12 source files — comfortably within this project's file-size conventions (200–400 lines typical, 800 max).

## 3. Dependencies

```toml
clap        4.5.20   # CLI parsing (derive)
serde       1.0.214  # (de)serialization
serde_json  1.0.132  # --json output
thiserror   2.0.3    # typed error enums
sha2        0.10.8   # evidence hashing
hex         0.4.3
time        0.3.36   # captured_at timestamps
image4      0.8.2    # IMG4 manifest parsing (pure Rust)
der         0.7
```

Dev-only: `tempfile 3.13.0`. Release profile enables `lto = true` and `strip = true`.

No C library or FFI boundary exists anywhere in the dependency graph — a deliberate deviation from `spec/build-spec.md`'s assumption of a C IMG4 library behind FFI (see §4).

## 4. Rules enforced by tooling, not just prose

Two checks run in `scripts/ci_guards.sh` and are tested with a negative case (a guard that doesn't fire on a violation would itself be a bug):

1. **No direct subprocess calls outside `wrapper.rs`.** Grepped for `std::process::Command` anywhere else in `src/`.
2. **No credential-shaped field anywhere.** Grepped for fields that look like a password/token/credential input.

Both guards, `cargo clippy --all-targets -- -D warnings`, and `cargo fmt --check` are clean as of this report. `--json` output is implemented on `evaluate`, `plan`, and `verify`.

## 5. Deviations from the literal spec text

All five of these exist because the referenced architecture document (spec §§9–10) is missing from the repo. Each is flagged in-code with a doc comment pointing back to this reasoning; none is an independent design decision overriding the missing document's authority.

- **1TR detection (`env.rs`).** No Apple API exists for this. Grounded in real research: `bputil -d` prints an "OS Type" line reading "one true recoveryOS" when paired, "ordinary recovery OS" in fallback. `env::detect()` checks for `/System/Library/CoreServices/Finder.app` first (absent in any Recovery-like runtime), then falls back to parsing that line. Fallback/"ordinary" recovery is treated as neither `MacOs` nor `OneTrueRecovery` — it fails closed.
- **State-machine edges (`plan.rs`).** Modeled conservatively: `Full → {ReducedKexts, PermissiveCustomKernel}`, and both of those only go back to `Full` — no direct `ReducedKexts ↔ PermissiveCustomKernel` edge.
- **`bputil`/`kmutil` command flags (`plan.rs`).** Taken from this machine's real `bputil --help` (v0.1.14) and `spec/build-spec.md`'s own worked `kmutil configure-boot` example. `PermissiveCustomKernel`'s plan includes `-s` (disable SSV) specifically because `contract-spec.md` requires `ssv_enabled == false` whenever `security_mode == Permissive`, resolving the spec in favor of the contract document over inferred binary behavior.
- **IMG4 library choice (`state/img4.rs`).** The pure-Rust `image4` crate, not a C library behind FFI. There is currently no `unsafe` on this path at all. Parsing is proven against malformed input and a real signed manifest (`tests/fixtures/image4_apticket.der`, vendored from the `image4` crate's own test suite). Not yet wired into `state::collect` — no confirmed path to a device's real LocalPolicy manifest without `bputil -d -j` or the missing architecture document.
- **`evidence.raw_outputs` scope (`state/collect.rs`).** `diskutil info /`, `diskutil apfs listVolumeGroups`, and `ioreg -c IOPlatformExpertDevice` all embed live, constantly-changing counters unrelated to boot security. Only the security-relevant reads (`csrutil authenticated-root status`, `bputil -d`) are recorded into `evidence.raw_outputs`; host-identification reads still go through the audited wrapper but aren't persisted into the hashed evidence set. Serial number is read via `system_profiler SPHardwareDataType` (confirmed stable across calls), not `ioreg` (confirmed unstable).
- **`other_containers` have no real policy data (`state/collect.rs`).** Populated via `diskutil apfs listVolumeGroups`, excluding the target's own group; each entry's `security_mode` is hardcoded `Unknown` rather than read from `bputil -d -v <uuid>`, to avoid multiplying credential-avoidance risk for a field that only needs to exist so P3's `SingleContainerTouched` invariant has something to diff.

## 6. What is not built

`authorize`, `execute`, and `verify`'s mutation logic (P3), the Permissive/custom-kernel path and `revert` (P4), and hardware-matrix fixtures/fuzzing/signed release bundling (P5) are **not implemented**. The module files exist as doc-comment-only stubs. This is a deliberate project boundary, not an oversight: P3 onward requires a disposable APFS scratch container and a human physically entering owner credentials in One True Recovery — neither of which can be exercised unattended in this session. See `reports/execution-product.md` §4 for what this means for the CLI surface today, and `reports/unlocked-bootloader-evidence.md` for the research track exploring whether a VM can substitute for real scratch hardware.

## 7. Test coverage

```
cargo test
# test result: ok. 44 passed; 0 failed; 0 ignored
```

Coverage spans `state::collect`'s fixture-driven parsers, `state`'s `ValidBootState` invariant checks (rejecting bad SHA-384 lengths, non-SEP-signed custom boot objects, custom kernels outside Permissive, future timestamps, non-disjoint containers, Permissive-with-SSV-enabled, etc.), `state::img4`'s manifest parsing against both garbage input and a real signed manifest, `wrapper`'s argv/exit-code/hash recording (including spawn failure and non-zero exit, both handled as data rather than panics), and `report`'s evidence-bundle writer.

## 8. Summary

P0–P2 constitute a complete, tested, read-only measurement-and-planning tool: it can tell an owner what security state their Mac is in and what a specific policy change would require, without ever mutating anything. The mutation half of the tool (P3–P5) is specified but not implemented, by design, pending access to a disposable scratch target. See the companion reports for the execution behavior of what is built, and the ongoing research into whether a VM can serve as that disposable target.
