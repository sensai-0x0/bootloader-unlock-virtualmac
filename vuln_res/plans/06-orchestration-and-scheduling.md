# 06 — Orchestration and scheduling

How plans `01`–`05` actually run as a connected pipeline rather than five scripts someone
has to remember to chain by hand.

## Trigger model

Three different cadences, not one:

1. **On every PR touching `src/state/img4.rs`, `src/main.rs`'s `cmd_verify`, or
   `scripts/ci_guards.sh`** — run `01`'s static-analysis agent (fast, no sandbox needed)
   as a CI check, same tier as the existing `cargo clippy`/`cargo fmt --check` gates in
   `../../CLAUDE.md`'s "Commands" section. This is the cheap, fast feedback loop.
2. **On a schedule (weekly is reasonable to start)** — `01`'s dependency/SBOM scan
   (`cargo audit`/`cargo deny`), since new advisories appear independent of any code
   change here.
3. **On demand, explicitly requested** — the full `02` → `03` → `04` → `05` fuzzing
   pipeline. This is not a "run on every commit" thing: it needs a sandboxed environment
   (`03`) that itself needs user sign-off to create, and a multi-minute-to-hours campaign
   isn't CI-gate material. Treat it like the root project treats `apply`/`revert` — a
   deliberate, asked-for action, not an automatic one.

## Agent handoff contract

Each stage writes its output to a fixed location the next stage reads from, so the
pipeline can be resumed or re-run at any stage without re-doing earlier work:

| Stage | Writes to | Next stage reads from |
|---|---|---|
| `01` | `vuln_res/sweep-reports/<sweep-id>/<slug>.md` | (terminal — these are usually just filed as issues/PRs directly) |
| `02` | `fuzz/fuzz_targets/*.rs`, `fuzz/corpus/*` | `03` |
| `03` | `fuzz/artifacts/<target>/*` (inside the sandbox; copied out after teardown) | `04` |
| `04` | `vuln_res/sweep-reports/<sweep-id>/<target>-<hash>.md` + minimized PoC fixture | `05` |
| `05` | A PR, an upstream issue link, or an escalation note, appended to the same finding file | (terminal) |

## Why this isn't one monolithic "vuln-research" agent

Each stage has a different tool dependency (clippy vs. cargo-fuzz vs. a sandbox runtime),
a different cadence (CI-gate vs. weekly vs. on-demand), and a different approval boundary
(fully automatic vs. "ask before installing a sandbox tool" vs. "a human reviews every
fix PR before merge"). Collapsing them into one agent would either over-trigger the
expensive stages on every commit, or under-trigger the cheap ones by batching everything
behind the slow stage's cadence. Keeping them separate, per this folder's `plans/README.md`
diagram, is what makes "quickly evaluating vulnerabilities" actually quick for the cheap
stages while still gating the expensive, sandbox-requiring ones properly.

## Exit gate for the whole suite

- `01` runs as a CI check and is green (or has tracked, non-blocking findings) on the
  current `main`.
- `02`+`03` have been run at least once end-to-end in an approved sandbox, producing at
  least a smoke-test-clean result (crash or no crash — either is a valid first run).
- If any crash was found: `04` and `05` have produced at least one complete
  finding-to-resolution cycle, proving the handoff contract works, not just that each
  stage works in isolation.
