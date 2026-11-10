//! `authorize` — P3 work (`spec/phased-plan.md`). Enforces the 1TR + typed-confirmation
//! precondition before any mutation (`spec/contract-spec.md`, `authorize.confirm()`).
//!
//! Deliberately empty in this build: this repo's current scope is P0–P2 (read-only
//! evaluate/plan), and this module's whole purpose is to gate mutation, so there is nothing
//! correct to implement here without `execute` and a real 1TR test environment to prove it
//! against. Stubbed out rather than omitted so the module layout from
//! `spec/build-spec.md` is visible in the tree.
