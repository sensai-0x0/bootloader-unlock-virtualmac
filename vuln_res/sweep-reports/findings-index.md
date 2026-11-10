# Cross-sweep findings index

One line per distinct finding, wherever it lives, most severe-and-open first. A finding
that reaches a working, engineered PoC also gets its own row in
[`exploits-index.md`](./exploits-index.md) — check there for anything clearly marked as
an exploit rather than a static finding.

| Finding | Score | Status | Sweep |
|---|---|---|---|
| [`ssv-enabled-contains-whole-blob`](./2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob.md) | 9 (3×1×3) | fixed (committed) | [2026-11-10-001-recon-verification](./2026-11-10-001-recon-verification/summary.md) |
| [`security-mode-full-contains-whole-blob`](./2026-11-11-001-host-independent-parsing-hardening/security-mode-full-contains-whole-blob.md) | 9 (3×1×3) | fixed, confirmed against real VM-captured `bputil -d` output | [2026-11-11-001-host-independent-parsing-hardening](./2026-11-11-001-host-independent-parsing-hardening/summary.md) |
| [`verify-baseline-no-size-cap`](./2026-11-11-001-host-independent-parsing-hardening/verify-baseline-no-size-cap.md) | 2 (1×1×2) | fixed | [2026-11-11-001-host-independent-parsing-hardening](./2026-11-11-001-host-independent-parsing-hardening/summary.md) |
| [`ci-guards-regex-boundary-gaps`](./2026-11-11-001-host-independent-parsing-hardening/ci-guards-regex-boundary-gaps.md) | n/a (operational) | fixed, self-test corpus added | [2026-11-11-001-host-independent-parsing-hardening](./2026-11-11-001-host-independent-parsing-hardening/summary.md) |
| [`agent-registry-not-live-this-session`](./2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md) | n/a (operational) | root-caused; harness feedback filed; working fallback documented | [2026-11-10-002-fallback-and-audit](./2026-11-10-002-fallback-and-audit/summary.md) |
| [`posture-confidence-missing-from-diff`](./2026-11-11-002-posture-confidence-recon/posture-confidence-missing-from-diff.md) | 6 (3×1×2) | fixed, one new regression test | [2026-11-11-002-posture-confidence-recon](./2026-11-11-002-posture-confidence-recon/posture-confidence-missing-from-diff.md) |
| [`env-1tr-fallback-detection-confirmed-broken`](./2026-11-11-003-license-policy-and-1tr-detection-gap/env-1tr-fallback-detection-confirmed-broken.md) | n/a (fail-closed functional gap, not a vuln) | **open** — escalated from AUDIT.md §2's "speculative" framing to confirmed; needs real research to close, not a code change | [2026-11-11-003-license-policy-and-1tr-detection-gap](./2026-11-11-003-license-policy-and-1tr-detection-gap/summary.md) |
| `cargo-deny-license-policy-gap` | n/a (operational) | fixed (`deny.toml` added) | [2026-11-11-003-license-policy-and-1tr-detection-gap](./2026-11-11-003-license-policy-and-1tr-detection-gap/summary.md) |

No fuzzer-confirmed or exploit-dev findings yet — no fuzz target has been built or run
(see `../plans/02-fuzzing-harness-agent.md`, not yet executed). All entries above are
static-analysis (or real-data-verification) findings, not fuzzer crashes.
