---
id: 2026-11-11-001-host-independent-parsing-hardening/verify-baseline-no-size-cap
target: main::cmd_verify (src/main.rs, pre-fix)
source: static-analysis (re-derived from vuln_res/AUDIT.md §1.2, not previously fixed)
status: fixed
score: 1 (reachability: local CLI only, no network) x 1 (memory-safety-weight:
  resource-exhaustion, not memory-unsafe) x 2 (blast radius: local DoS of the invoking
  process only) = 2
discovered_by: vulnres-recon-style static review (prior sweep, `vuln_res/AUDIT.md` §1.2);
  fixed in this sweep
sweep: ../INDEX.md#2026-11-11-001-host-independent-parsing-hardening
discovered_at: 2026-11-10 (AUDIT.md); fixed 2026-11-11
---

## Short description

`verify --baseline <path>` deserialized an arbitrary file straight into a `BootState` with
no size check beforehand. A very large (not necessarily deeply nested — `serde_json`'s own
recursion limit already bounds that axis) JSON file passed as `--baseline` could force a
large allocation before `serde_json` gets a chance to reject it — a cheap local
denial-of-service against whoever runs `verify` against a baseline file they didn't
produce themselves (one emailed to them, or fetched by an automated pipeline).

## Technical detail

`src/main.rs::cmd_verify`, pre-fix:

```rust
fn cmd_verify(baseline_path: PathBuf, json: bool) -> ExitCode {
    let baseline_json = match std::fs::read_to_string(&baseline_path) {
        ...
    };
    let baseline: state::BootState = match serde_json::from_str(&baseline_json) {
        ...
    };
```

No `std::fs::metadata` check, no size cap — the entire file is read into a `String` and
handed to `serde_json` regardless of size.

## Classification

- **Type:** resource-exhaustion (local DoS), not memory-unsafety
- **Reachability:** 1 — this is a local CLI tool, not a network service; the project's own
  threat model (per `AUDIT.md` §1.2) doesn't include "run `verify` against a baseline from
  an untrusted party" as a primary scenario today, but the boundary principle
  (`spec/build-spec.md`'s "validate all external data," mirrored in the root `CLAUDE.md`)
  applies regardless of how likely the scenario is
- **Blast radius:** 2 — affects only the invoking process (memory/CPU exhaustion), no
  persistence, no effect on any other part of the system

Severity is low (hence the low score relative to the two `SecurityMode`-parsing findings
in this sweep), but the fix costs almost nothing and closes a boundary the project's own
coding standards already commit to.

## Reproduction

Not a crash — the point is to prevent one from ever being possible rather than reproduce
one. `src/main.rs`'s `tests::oversized_baseline_file_is_rejected_before_parsing` proves the
guard fires (a file just over the limit is rejected with `PARSE_ERROR`, before any JSON
parsing is attempted) rather than relying on `serde_json` to eventually reject malformed
content after already allocating for it.

## Resolution

**Fixed directly:**

- Added `MAX_BASELINE_FILE_BYTES` (1 MiB — generous headroom over a real `BootState`'s
  actual size, which is a few KB) to `src/main.rs`.
- `cmd_verify` now calls `std::fs::metadata` on the baseline path first and refuses to read
  the file at all if it exceeds the cap, with a clear error message naming the actual size
  and the limit.
- Two tests added: `oversized_baseline_file_is_rejected_before_parsing` (proves the size
  guard fires on a file that's valid-looking in every way except size) and
  `missing_baseline_file_is_a_clean_error_not_a_panic` (adjacent coverage — confirms the
  existing missing-file path still degrades cleanly after the new metadata check was
  inserted ahead of it).
- Verified: `cargo test` 55/55 passing, `cargo clippy --all-targets -- -D warnings` clean,
  `cargo fmt --check` clean.
