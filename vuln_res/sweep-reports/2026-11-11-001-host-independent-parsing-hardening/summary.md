# Sweep summary — 2026-11-11-001-host-independent-parsing-hardening

**Trigger:** user asked to review this project's findings, confirm the tool is
"well-rounded and effective regardless of the host," identify any outlying/unfinished
work, and complete it.

**Scope:** `vuln_res/AUDIT.md`'s three open, low-risk, no-host-install-required findings
(§1.2 DoS hardening, §2 brittle text-parsing, §3 CI guard regex gaps) — deliberately
excluding §1.1 (DER fuzzing) and §4 (`cargo audit`/`cargo deny`), both of which need a new
host-level tool install and so need the user's explicit go-ahead first, per
`vuln_res/CLAUDE.md`'s execution posture.

**What actually happened, beyond the audit's original scope:** while reviewing §2 against
this project's own real `bputil -d` captures (from the M8-M10 VM research track,
`progress/milestones.md`), confirmed the `Full`-detection branch doesn't just carry a
*theoretical* risk — it currently cannot classify any real captured output as `Full` at
all, because of a whitespace mismatch between the hand-typed check and Apple's actual
column-padded output. This is the sweep's headline finding
(`security-mode-full-contains-whole-blob.md`): a correctness bug that was present in the
committed code, confirmed via real evidence, not discovered by guessing.

## Findings

1. [`security-mode-full-contains-whole-blob`](./security-mode-full-contains-whole-blob.md)
   — score 9 — fixed, with three new real fixtures and four new regression tests
2. [`verify-baseline-no-size-cap`](./verify-baseline-no-size-cap.md) — score 2 — fixed,
   with two new tests
3. [`ci-guards-regex-boundary-gaps`](./ci-guards-regex-boundary-gaps.md) — operational
   finding, not scored — fixed, with a new self-test script

## Verification

- `cargo test`: 55/55 passing (up from 49 at the start of this sweep)
- `cargo clippy --all-targets -- -D warnings`: clean
- `cargo fmt --check`: clean
- `./scripts/ci_guards.sh`: green against the real tree
- `./scripts/ci_guards_selftest.sh` (new): all-pass against the gap corpus

## New knowledge

- `bputil -d` prints *two* lines containing "Security Mode" — a numeric one tagged
  `(CSEC)` near the top of the local-policy block, and a human-readable one tagged
  `(smb0)`/`(smb0 && smb1)` near the bottom. Any future parser touching this output needs
  to anchor on which one it means, not just the substring "security mode".
- `CSEC` was `1` in every captured state (`Full`, `Reduced`, `Permissive`) — it does not
  appear to toggle `0`/`1` based on `SecurityMode` the way the pre-fix code assumed. Worth
  keeping in mind if a future change is tempted to reintroduce a `(CSEC)`-based check.
- `tests/fixtures/`'s `_VM_VIRTUALIZED` label (new in this sweep) is the right category for
  a real capture from a disposable VM this project controls — distinct from `_REDACTED`
  (real device), `_SYNTHETIC` (hand-built), and `_FIRMWARE_TEMPLATE` (real firmware, no
  live device). See `tests/fixtures/README.md`.

## Not done, and why

- §1.1 (fuzz harness for `state/img4.rs`) and §4 (`cargo audit`/`cargo deny`) both need
  `cargo-fuzz`/`cargo-audit` installed, which is a new host-level footprint —
  `vuln_res/CLAUDE.md`'s execution posture requires stopping to ask first, every time, not
  assuming a prior approval carries forward. Not attempted in this sweep.
- `env.rs:72`'s 1TR-pairing substring check (`AUDIT.md` §2's other named instance) was
  *not* touched: unlike `parse_security_mode`, it's already anchored to a single found line
  (the "OS Type" line), and the audit's concern there is a more speculative future-wording
  scenario ("NOT one true recoveryOS") rather than a confirmed-broken-today bug like this
  sweep's headline finding. Left as a flagged-but-lower-priority item rather than inventing
  a fix for a hypothetical Apple string that's never been observed.
