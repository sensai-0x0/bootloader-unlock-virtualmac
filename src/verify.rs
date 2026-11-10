//! `verify` — re-measures and asserts the global invariants from `spec/contract-spec.md`
//! after a mutation, failing closed (`verify.assert_invariants`). Also used read-only by the
//! `verify` CLI subcommand to diff a baseline against a fresh measurement.
//!
//! The pure, no-mutation half of this module (comparing two already-collected `BootState`s)
//! is really [`crate::state::diff::diff`], already implemented in P2. What's stubbed out
//! here is asserting the global invariants themselves (`ReadOnlyUnlessGated`,
//! `SingleContainerTouched`, etc.) against a real before/after pair from an actual mutation —
//! that has no meaningful implementation before `execute` exists in P3.
