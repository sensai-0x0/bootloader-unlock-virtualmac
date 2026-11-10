---
id: 2026-11-11-002-posture-confidence-recon/posture-confidence-missing-from-diff
target: state::diff::diff (src/state/diff.rs, pre-fix)
source: static-analysis
status: fixed
score: 3 (reachability) x 1 (memory-safety-weight: logic-only) x 2 (blast radius) = 6
discovered_by: vulnres-recon (01-static-analysis-and-dependency-agent.md sweep)
sweep: ../INDEX.md#2026-11-11-002-posture-confidence-recon
discovered_at: 2026-11-11
---

## Short description

The `posture_confidence` field was added (commits `a0cdd5e`/`20da5e6`) specifically so a
consumer can tell "measured Full" apart from "unmeasured" — the evaluator's own binding
guardrail for that work is "honesty of state — must surface unmeasured louder"
(`reports/evaluator/evaluator-decisions-2026-11-11.md`, D2). But `state::diff::diff` —
the exact function `verify` (live today) and the future P3 invariant-assertion path use
to report what changed between two `BootState`s — never compared `posture_confidence` at
all. Two states that are identical in every other respect but disagree about how
trustworthy the measurement is (e.g. one claims `Measured`, the other `UntrustedRead`)
produced **zero** diff entries, silently defeating the one thing this field was built to
guarantee.

## Technical detail

`src/state/diff.rs`'s `diff()` walks `BootState` field-by-field with a `compare!` macro,
explicitly listing `environment`, `target_container.security_mode`,
`target_container.ssv_enabled`, `target_container.allows_custom_kernel`,
`target_container.allows_third_party_kexts`, `enrolled_objects`, and `other_containers`.
`posture_confidence` — a top-level `BootState` field added alongside those others in the
same recent work — was never added to that list.

Within a single live `collect()` pass this is largely masked: `collect()`'s own
`derive_posture_confidence` (`src/state/collect.rs`) always forces `security_mode` to
`Unknown` on exactly the same paths that produce `PostureConfidence::UntrustedRead`, so a
*same-session* confidence downgrade also shows up as a `security_mode` change that
`diff()` does catch. The gap is real at the schema boundary, though: `verify --baseline
<path>` (`src/main.rs:175`, live today) deserializes an arbitrary, possibly
externally-authored `BootState` file as the "before" side of the comparison —
`vuln_res/AUDIT.md` §1.2 already flags this exact file as attacker-influenceable input
("a baseline someone emailed you, or fetched as part of an automated pipeline"). A
baseline that claims `Measured` confidence for a given `security_mode`/`ssv_enabled`
combination, diffed against a fresh read that independently arrives at the same
`security_mode`/`ssv_enabled` but only with `UntrustedRead` confidence (or vice versa:
a stale/legacy baseline defaulting to `Unmeasured` per the serde default, diffed against
a genuinely `Measured` fresh read), reports **no difference at all** — even though the
confidence claim is exactly the dimension that changed. This is the same "silently
reduces detection fidelity without saying so" failure mode `AUDIT.md` §2 already
documented for brittle `.contains()` parsing, just manifesting as a missing comparison
rather than a missing anchor.

Pre-fix `diff()` (abridged):

```rust
pub fn diff(before: &BootState, after: &BootState) -> Vec<DiffEntry> {
    let mut entries = Vec::new();
    // ... compare! macro defined here ...
    compare!("environment", before.environment, after.environment);
    compare!("target_container.security_mode", ...);
    // posture_confidence never appears anywhere in this function.
    ...
}
```

## Reproduction

```
$ cargo test state::diff::tests::a_posture_confidence_change_is_reported_even_when_security_mode_is_unchanged
```

Against the pre-fix implementation, this assertion fails: `diff()` returns an empty
`Vec<DiffEntry>` for two `BootState`s that differ only in `posture_confidence`
(`Measured` vs. `UntrustedRead`, same `security_mode: Full` and all other fields equal).

PoC artifact: none — this is a missing-comparison logic bug, not a crash/hang/memory-
safety issue; the unit test above is the reproduction.

## Classification

- **Type:** logic-divergence (a real state change is silently absent from the reported
  diff)
- **Reachability:** 3 — `state::diff::diff` is called today by the live `cmd_verify` CLI
  path (`src/main.rs:219`), not a P3-only stub; any `verify --baseline <path>` invocation
  exercises the buggy comparison set.
- **Blast radius:** 2 — does not itself flip `SecurityMode` or any `is_mutation_allowed()`
  gate (today's `verify` subcommand is read-only and doesn't drive a mutation decision on
  its own), but it directly undermines the one invariant `posture_confidence` exists to
  provide ("surface unmeasured louder") for exactly the field designed to carry that
  signal into the report. Would matter more once P3's `verify.assert_invariants` consumes
  this same `diff()` output to decide whether a post-mutation state is honestly measured.

## Chaining notes

Checked against this sweep's other work and the two prior sweeps' findings — this does
not compose with `security-mode-full-contains-whole-blob` or `verify-baseline-no-size-cap`
(different code paths, no shared trigger). Nothing to chain.

## Resolution

**Fixed directly** in this sweep, following the same Case A posture as the prior two
sweeps:

- `src/state/diff.rs`: added a `compare!("posture_confidence", ...)` entry, placed
  immediately after `environment` (both are top-level `BootState` fields, not nested
  under `target_container`), with a doc comment explaining why this field is compared at
  all and linking back to the evaluator decision that motivated it.
- One new regression test,
  `a_posture_confidence_change_is_reported_even_when_security_mode_is_unchanged`, proving
  two states identical except for `posture_confidence` now produce exactly one diff entry
  at that path.
- Verified: `cargo test` 63/63 passing (up from 62), `cargo clippy --all-targets -- -D
  warnings` clean, `cargo fmt --check` clean, `./scripts/ci_guards.sh` and
  `./scripts/ci_guards_selftest.sh` both green.
