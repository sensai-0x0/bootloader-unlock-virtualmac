# 02 — Fuzzing harness agent

Builds the actual fuzz targets for the two parsers `AUDIT.md` §1 identified. Both are pure
functions with no side effects, which is exactly what makes them cheap and safe to fuzz —
no filesystem writes, no subprocess calls, nothing that could touch anything outside the
process's own memory.

## Toolchain

`cargo fuzz` (libFuzzer-based, coverage-guided) — not installed on this host today;
installing it is a host-level change, same stop-and-ask as `cargo audit`/`cargo deny` in
`01-static-analysis-and-dependency-agent.md`. Once approved, it adds a `fuzz/` workspace
member (standard `cargo fuzz init` layout) alongside the existing `src/`.

## Target 2.1 — `img4_decode`

```rust
// fuzz/fuzz_targets/img4_decode.rs
#![no_main]
use libfuzzer_sys::fuzz_target;
use bputil_eval::state::img4::{parse_manifest_der, facts};

fuzz_target!(|data: &[u8]| {
    if let Ok(manifest) = parse_manifest_der(data) {
        let _ = facts(&manifest); // don't care about the Result, only about crashes/hangs
    }
});
```

(`parse_manifest_der`/`facts` are currently `#[cfg_attr(not(test), allow(dead_code))]` —
the harness agent's first job is making them reachable from a `lib.rs` or `pub(crate)`
re-export the fuzz crate can call, without changing their production-code dead-code status
outside of `cfg(fuzzing)`.)

**Seed corpus:**
- `tests/fixtures/image4_apticket.der` (already in-repo).
- Any additional *structurally real* IM4M manifests found via the `image4` crate's own
  upstream test suite (same license, same provenance as the existing fixture) — not
  anything extracted from the real firmware under `../research/`, which `../CLAUDE.md`
  permits reading for structural reference but not for exploit-corpus seeding specifically
  against Apple's own signed manifests. Using the crate's own public test vectors avoids
  that line entirely while still getting real-shaped DER.
- A handful of hand-crafted boundary cases: truncated length fields, nested SEQUENCE
  depth near whatever `der`'s configured recursion limit is, zero-length OCTET STRINGs.

**Run under:** `cargo fuzz run img4_decode -- -rss_limit_mb=2048` with ASan (cargo-fuzz's
default sanitizer) to catch memory-safety issues, not just panics.

## Target 2.2 — `boot_state_deserialize`

```rust
// fuzz/fuzz_targets/boot_state_deserialize.rs
#![no_main]
use libfuzzer_sys::fuzz_target;
use bputil_eval::state::BootState;

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        let _ = serde_json::from_str::<BootState>(s);
    }
});
```

This directly exercises the path `cmd_verify` (`src/main.rs:174`) uses on a user-supplied
file. Goal: stack-overflow/resource-exhaustion via deep nesting or huge arrays in
`enrolled_objects`/`other_containers`/`evidence.raw_outputs`, per `AUDIT.md` §1.2.

**Seed corpus:** every `BootState` the project already serializes in its own tests —
`tests/fixtures/plans/*.json`'s embedded baselines, plus a few `cargo run -- evaluate
--json` captures from this (or a disposable VM's) real run.

## What the harness agent actually does (not just "write the two files above")

1. Scaffolds `fuzz/` via `cargo fuzz init`, wires both targets, confirms each builds and
   runs for a short smoke duration (seconds, not a full campaign) before handing off.
2. Confirms `cargo fuzz` is building the parsing crates (`image4`, `der`, `serde_json`)
   with the fuzzer's own instrumented profile — not accidentally fuzzing a cached, 
   non-instrumented build.
3. Writes the corpus directories (`fuzz/corpus/img4_decode/`,
   `fuzz/corpus/boot_state_deserialize/`) and seeds them per above.
4. Hands off to `03-sandboxed-execution-environment.md` for where the actual
   multi-hour/overnight campaign runs — this agent's job ends at "the target builds and
   finds its first crash (or doesn't, in a short smoke run) correctly."

## Exit gate

Both fuzz targets build, run a 60-second smoke test each with no setup errors, and are
checked into `fuzz/` with seeded corpora — ready to hand to the sandboxed campaign runner.
No campaign has run at length on the host itself.
