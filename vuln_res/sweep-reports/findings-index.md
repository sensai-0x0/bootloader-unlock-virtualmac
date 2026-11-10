# Cross-sweep findings index

One line per distinct finding, wherever it lives, most severe-and-open first.

| Finding | Score | Status | Sweep |
|---|---|---|---|
| [`ssv-enabled-contains-whole-blob`](./2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob.md) | 9 (3×1×3) | fixed (uncommitted) | [2026-11-10-001-recon-verification](./2026-11-10-001-recon-verification/summary.md) |
| [`agent-registry-not-live-this-session`](./2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md) | n/a (operational) | open | [2026-11-10-001-recon-verification](./2026-11-10-001-recon-verification/summary.md) |

No fuzzer-confirmed or exploit-dev findings yet — no fuzz target has been built or run
(see `../plans/02-fuzzing-harness-agent.md`, not yet executed). Both entries above are
static-analysis findings from the first real sweep.
