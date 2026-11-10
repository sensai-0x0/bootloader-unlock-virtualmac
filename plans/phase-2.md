# Phase 2 — Planner: remaining steps

Status: done against this phase's exit gate for the transitions the code currently models.
`plan()` emits correct `PlannedTransition`s for `Full -> ReducedKexts`,
`Full -> PermissiveCustomKernel`, and the two revert-to-`Full` edges, using `bputil` flags
confirmed against this machine's real `bputil --help`. What's below closes the remaining
honesty gaps noted in `CLAUDE.md`'s "Deviations from the literal spec text".

## 1. Resolve the state-machine edges against the real diagram, if it ever surfaces

`src/plan.rs`'s `is_permitted` function models a conservative state machine (`Full` can go
to either mutating profile; both mutating profiles can only revert to `Full`; no direct
`ReducedKexts <-> PermissiveCustomKernel` edge) because `spec/contract-spec.md` references
a diagram of "the only legal transitions" that isn't present in this repo's extracted text.

If the companion architecture document (`spec/build-spec.md` and `spec/contract-spec.md`
both cite "sections 9–10" of it) ever becomes available:
1. Check its state-machine diagram against `is_permitted()` in `src/plan.rs`.
2. If it adds an edge (e.g. a direct `ReducedKexts -> PermissiveCustomKernel`), add the
   corresponding match arm, a `commands_for` entry, and a test mirroring the existing
   `full_to_permissive_includes_kmutil_enrolment`-style tests.
3. Update the doc comment at the top of `src/plan.rs` and the corresponding bullet in
   `CLAUDE.md` to say the edges are now transcribed, not modeled.

## 2. Verify the `bputil`/`kmutil` flags against the architecture document too

Same situation: `commands_for()` in `src/plan.rs` uses flags confirmed against this
machine's installed `bputil --help` (v0.1.14) and the worked `kmutil configure-boot`
example from `spec/build-spec.md`'s `PlannedTransition` sample — reasonable, but not
independently verified against whatever the architecture document's sections 9–10 actually
specify. In particular, double-check:
- Whether `PermissiveCustomKernel` should include `-s` (disable SSV) as this code assumes
  (chosen because `spec/contract-spec.md` requires `ssv_enabled == false` under Permissive,
  even though `bputil --help`'s wording for `-n` alone doesn't explicitly say it disables
  SSV) — or whether the architecture document specifies a different combination.
- The exact `kmutil configure-boot` argument for the custom boot object's path (currently a
  literal placeholder, `<custom-boot-object-path>`, in `commands_for`'s
  `PermissiveCustomKernel` arm) — this needs a real value before P4 can run it for real.

## 3. ~~Golden-file tests as separate files~~ — done

`tests/fixtures/plans/` now has one committed JSON fixture per transition
(`full_to_reduced_kexts.json`, `full_to_permissive_custom_kernel.json`,
`reduced_to_full_revert.json`, `permissive_to_full_revert.json`), generated from `plan()`
itself and then frozen. `src/plan.rs`'s `golden_*` tests diff fresh `plan()` output against
them via `serde_json::Value` equality. Negative-tested: editing a fixture to say `-X`
instead of `-k` makes the corresponding test fail with a readable diff, confirming this
actually catches drift rather than trivially passing. The original inline assertion tests
(`full_to_reduced_kexts_is_permitted_and_uses_bputil_flags`, etc.) are kept alongside these —
they test specific properties (which tool, which flags are present) independently of exact
JSON shape, which is a useful second angle on the same code.

If item 1 or 2 above ever changes `commands_for`/`is_permitted`, the golden fixtures need
regenerating too — see the (now-removed) one-off generator pattern in this file's git
history (`src/plan.rs`, commit that added these tests) for how they were produced the first
time.

## 4. Multi-volume targets (shared with phase-1.md item 3)

`plan()` takes its `target_volume_group` from whatever `collect()` produced, which is
always the root volume today. No action needed until `evaluate --volume <v>` exists.
