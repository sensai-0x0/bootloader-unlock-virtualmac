---
name: build-test-clippy-fmt-clean-2026-11-10
type: target-status
description: cargo build/test/clippy/fmt all clean at commit 1b37d16, 2026-11-10
updated: 2026-11-10
---

`cargo build` — clean (0.42s). `cargo test` — 44/44 passing at the start of this sweep
(the root `../../CLAUDE.md`'s own prior claim was "43 tests" — already one more than
that before this sweep touched anything). `cargo clippy --all-targets -- -D warnings` —
clean, zero warnings. `cargo fmt --check` — clean, no diff. All confirmed by actually
running them (see [[../sweep-reports/2026-11-10-001-recon-verification/summary]]).

**Updated same sweep:** after fixing
[[../sweep-reports/2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob]]
(5 new regression tests), the count is **49/49 passing**, clippy still clean, fmt still
clean (after one `cargo fmt` auto-format pass). This entry's test count is now stale the
moment any further test is added — treat "49" as a snapshot at the end of this sweep,
not a fact to assume holds without re-checking.

A future sweep: don't re-run these as a first step if the commit hash hasn't changed —
re-run only after a code change, or periodically to catch toolchain-version drift.
