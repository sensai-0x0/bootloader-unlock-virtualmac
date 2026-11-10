# Cross-sweep findings index

One line per distinct finding, wherever it lives, most severe-and-open first. A finding
that reaches a working, engineered PoC also gets its own row in
[`exploits-index.md`](./exploits-index.md) — check there for anything clearly marked as
an exploit rather than a static finding.

| Finding | Score | Status | Sweep |
|---|---|---|---|
| [`ssv-enabled-contains-whole-blob`](./2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob.md) | 9 (3×1×3) | fixed (committed) | [2026-11-10-001-recon-verification](./2026-11-10-001-recon-verification/summary.md) |
| [`agent-registry-not-live-this-session`](./2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md) | n/a (operational) | root-caused; harness feedback filed; working fallback documented | [2026-11-10-002-fallback-and-audit](./2026-11-10-002-fallback-and-audit/summary.md) |

No fuzzer-confirmed or exploit-dev findings yet — no fuzz target has been built or run
(see `../plans/02-fuzzing-harness-agent.md`, not yet executed). Both entries above are
static-analysis findings from the first real sweep.
