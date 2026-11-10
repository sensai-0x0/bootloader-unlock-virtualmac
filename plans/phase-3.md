# Phase 3 — Executor, authoriser, verifier: not started

**This phase mutates a real Mac's boot security policy.** Per `spec/build-spec.md`'s golden
rules, that only happens from One True Recovery with a human owner physically present to
type their own credentials. Nothing here should be done by an unattended agent — these are
instructions for **you**, optionally with an agent pair-programming at the keyboard while
you're the one driving 1TR and typing credentials.

## Prerequisites — do these before writing any code

1. **A disposable Mac, or at minimum a disposable scratch APFS container on a Mac you can
   afford to DFU-restore if something goes wrong.** `spec/phased-plan.md`'s own risk
   register flags "a scratch-container mistake bricks a test Mac" as high-impact; have a
   DFU-restore runbook ready and tested *before* the first `apply` call, not after a
   problem. Never run this phase's work against your primary machine.
2. **Try to get the missing companion architecture document.** `spec/build-spec.md` and
   `spec/contract-spec.md` both cite it (sections 9–10) for exact module behaviour. P0–P2
   worked around its absence by researching and documenting every gap (see `CLAUDE.md`'s
   "Deviations" section) — that approach gets riskier once code actually mutates boot
   policy. At minimum, re-read `phase-2.md` items 1–2 and resolve them first.
3. **Decide how you'll create the scratch container.** `diskutil apfs addVolume` or
   similar, sized for a minimal test install. Confirm you can boot it and reach it from
   1TR before writing `authorize`/`execute` code against it.

## Implementation, in the order the safety gates demand

`spec/phased-plan.md`'s "Safety gates that block a mutating phase" are the checklist — all
four must hold before and throughout this phase:

1. The read-only path is side-effect-free (already proven — see `CLAUDE.md`).
2. The audited wrapper is the only route to a subprocess (already CI-guarded).
3. `authorize.confirm` cannot be satisfiable non-interactively.
4. `verify` runs after every mutation and its failure cannot be swallowed.

Build in this order:

### 1. `src/env.rs` — nothing to add, but re-verify against real 1TR

`is_mutation_allowed()` is already implemented and unit-tested for the macOS branch. It has
**never been run from inside actual 1TR** — do that first, by itself, before building
anything on top of it:
```
cargo build --release
# boot the scratch Mac into 1TR, open Terminal there, run the built binary's `evaluate`
```
Confirm `environment` reports `OneTrueRecovery` and `is_mutation_allowed()` (surfaced today
via `evaluate`'s human-readable output line) reports `true`. If the `bputil -d` "OS Type"
string doesn't say "one true recoveryOS" the way `env.rs`'s module doc comment expects
(a MacRumors forum report cited there warned this might vary), fix the detection *here*
before anything downstream depends on it.

### 2. `src/authorize.rs`

Implement `confirm(plan: &PlannedTransition) -> Result<Confirmation, AuthorizeError>`:
- `requires: is_mutation_allowed() == true` — call `env::is_mutation_allowed()` and bail
  immediately (exit 10, `PreconditionNotMet`) if false, per `spec/contract-spec.md`.
- Print the plan's `commands`, `consequences`, and `requires` **verbatim** (per
  `spec/build-spec.md`: "An operate agent presenting a plan to a human MUST show commands,
  consequences and requires verbatim").
- Prompt for a typed confirmation of something specific to this plan (e.g. require the user
  to type the target profile name back) — not a bare y/n, so it can't be fat-fingered into
  approving the wrong transition.
- `Confirmation` holds no secret and cannot be constructed any other way. Add a type-level
  guard (e.g. a private field, constructible only inside this module) so nothing else can
  fabricate one.
- **Never** read a username/password here — that prompt belongs to `bputil` itself, later,
  inside `execute::run`.

### 3. `src/execute.rs`

Implement `run(plan: &PlannedTransition, _confirmation: &Confirmation) -> Result<RawResults, ExecuteError>`:
- Re-check `is_mutation_allowed()` and that every `argv[0]` in `plan.commands` is one of
  `bputil`, `kmutil`, `csrutil` — reject anything else (this is the property
  `scripts/ci_guards.sh` can't check; it needs a runtime test instead, see below).
- Run `plan.commands` **in order**, through `crate::wrapper::run`, and nothing else. Stop
  at the first non-zero exit (`spec/contract-spec.md`: exit 12 `TransitionFailed`, baseline
  preserved, stderr reported).
- This is where `bputil`'s own interactive username/password prompt happens naturally — do
  not pass `-u`/`-p` from this code.

### 4. `src/verify.rs`

Implement `assert_invariants(baseline: &BootState, fresh: &BootState) -> Vec<InvariantResult>`:
- `ReadOnlyUnlessGated`, `SingleContainerTouched`, `Reversible`, `NoCredentialHandling`,
  `SupportedMechanismsOnly`, `MeasuredTruth`, `EvidenceComplete`, `OwnershipConfirmed` — one
  result per invariant, per `spec/contract-spec.md`'s "Global invariants" table.
- `SingleContainerTouched` needs `phase-1.md`'s item 4 (`other_containers` populated) done
  first — otherwise there's nothing to diff against.
- This is a pure function of `(baseline, fresh)` — make it exhaustively unit-testable
  without touching a real device, the same way `src/state/diff.rs` already is.
- Wire a *negative* test: construct a `fresh` `BootState` that's wrong in a way that should
  trip `SingleContainerTouched` or `ReadOnlyUnlessGated`, and assert `assert_invariants`
  catches it. `spec/phased-plan.md`'s exit gate explicitly requires this ("a deliberately
  wrong post-state is caught by verify").

### 5. Wire `apply`/`revert` in `src/main.rs`

Replace the current stub arm (`Command::Apply | Command::Revert => { eprintln!("not
implemented..."); ... }`) with the real pipeline: `collect()` a fresh baseline ->
`authorize::confirm` -> `execute::run` -> re-`collect()` -> `verify::assert_invariants` ->
build and write a `Report` via `report::write_bundle`. Exit codes per
`spec/build-spec.md`'s table (10/12/13 as appropriate).

### 6. The round trip, on the scratch container only

`full -> reduced -> full`:
```
cargo run --release -- evaluate --json > baseline.json   # confirm Full first
# reboot to 1TR
cargo run --release -- plan reduced-kexts --json > plan.json
cargo run --release -- apply --plan plan.json
# back in macOS:
cargo run --release -- verify --baseline baseline.json
# reboot to 1TR again:
cargo run --release -- plan full --json > revert_plan.json
cargo run --release -- apply --plan revert_plan.json
```
(`apply --plan <file>` per `spec/build-spec.md`'s CLI table — `src/main.rs`'s `Apply`
variant currently takes no arguments; add the `--plan` flag when you wire this in step 5.)

Confirm: `verify` after the reduce shows exactly the expected fields differing (security
mode, kext trust) and nothing else; `verify` after the revert shows the state back to the
original baseline.

### Exit criteria for this phase

All five items from `spec/phased-plan.md`'s P3 exit gate, demonstrated with evidence
bundles, not just a clean test run:
- [ ] Round trip verified on a scratch container.
- [ ] `apply` in macOS (not 1TR) returns exit 10 and changes nothing — test this for real,
      not just via `is_mutation_allowed`'s existing unit test.
- [ ] `execute::run` rejects a hand-crafted `PlannedTransition` containing a command not in
      the allowed-tools list, or an argv not equal to what a legitimate `plan()` call would
      have produced.
- [ ] A deliberately wrong post-state is caught by `verify` as exit 13.
- [ ] `authorize::confirm` is proven non-satisfiable without an interactive terminal (e.g.
      piping `/dev/null` to stdin and confirming it refuses rather than defaulting to yes).

Only once every box above is checked does `phase-4.md` become safe to start.
