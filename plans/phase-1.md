# Phase 1 — Evaluator: remaining steps

Status: done against this phase's exit gate. `evaluate`/`report` work, run on real hardware,
and `evaluate --json` run twice differs only in `captured_at` (verified, not assumed — see
`CLAUDE.md`'s "What's verified, concretely"). What's below are follow-ups that make P1
stronger, not blockers for moving on to the planner work in `phase-2.md`.

## 1. Wire `state/img4` into `state/collect`

Right now `BootState.enrolled_objects` is always an empty `Vec` — `state/collect.rs` never
calls `state::img4::parse_manifest_der`. The original P1 workstream in
`spec/phased-plan.md` ("fold manifest hashes and signers into `enrolled_objects`") is
unimplemented.

This needs a real manifest to read from the device, which in turn needs figuring out
**where the LocalPolicy's IM4M actually lives on disk** for a booted macOS system — that's
exactly the kind of detail the missing companion architecture document would specify, and
guessing a filesystem path to do a destructive-adjacent (even if read-only) poke at
undocumented local-policy storage is the wrong way to find out. Concretely:

1. First, do `phase-0.md`'s item 1 (prove the parser against a real manifest) — that's
   pure library plumbing, no device path required.
2. Then, separately, find out how `bputil -d` (or `-j`) itself exposes the manifest body —
   its `-d -j` JSON output (see `phase-0.md` item 2) may already give you the per-object
   hashes and signer info directly, without this module needing to locate and parse a raw
   `.im4m` file itself at all. Check that before building a file-path-guessing approach.
3. Only if `bputil -d -j` doesn't expose this does it become worth tracking down the
   on-disk IM4M path — and at that point, this is genuinely architecture-document
   territory: stop and get that document, or get explicit sign-off on wherever you're about
   to read from.

## 2. Add a real `bputil -d` fixture-driven test for `security_mode`

Covered in `phase-0.md` item 2 — listed here too because it's as much a P1 parser-coverage
item as a P0 fixtures-harness one.

## 3. Multi-volume / non-root-volume targets

`state/collect::collect()` always targets `/` (the root volume). `evaluate --volume <v>`
from `spec/build-spec.md`'s CLI table implies arbitrary volume targeting. Not needed until
something exercises a second bootable volume (e.g. P3's scratch-container work), so leave
this until `phase-3.md` actually needs it rather than building it speculatively now.

## 4. ~~`other_containers`~~ — done

`collect()` now populates `other_containers` via `diskutil apfs listVolumeGroups`
(`extract_other_containers` in `src/state/collect.rs`), excluding the target's own volume
group. `security_mode` for each is always `SecurityMode::Unknown` — reading another
container's real policy needs `bputil -d -v <that-uuid>` under `sudo`, which is deliberately
out of scope here for the same non-interactive-credential reasons the target container's
own read already is (see this module's doc comment). That's enough for `SingleContainerTouched`
(P3's `verify`) to have something to diff against; it doesn't need real per-container policy
data to do that job.

Caveat: this development machine only has one real APFS volume group, so the "exclude the
target, keep the others" branch is tested against a hand-built synthetic fixture
(`tests/fixtures/diskutil_apfs_listVolumeGroups_SYNTHETIC_multi.txt`), not a real multi-group
capture. If a machine with a genuine second bootable volume group becomes available, replace
it with a real redacted capture (see `tests/fixtures/README.md`).

## 5. Posture-confidence follow-ups (evaluator "Build next" rank 1)

`reports/evaluator/evaluator-decisions-2026-11-11.md`'s "Build next" rank 1 is in flight:
`PostureConfidence` (`Measured`/`UntrustedRead`/`Unmeasured`) and a
`BootState.posture_confidence` field exist in `src/state/mod.rs` (serde-defaulting to
`Unmeasured` on legacy baselines, so nothing overclaims).

**Landed 2026-11-11 (`feat/posture-confidence-fields`).** Schema step complete: enum +
field + serde default + three new unit tests (legacy-baseline deserialises as
`Unmeasured` and never upgrades its own claim; all three variants pass `validate()`;
serialisation carries the field); every `BootState` literal updated (collect/diff/plan/
report); quantity gates live-green — 58 tests, `clippy -D warnings`, `fmt`, both
`ci_guards.sh` guards, and the P1 twice-run gate re-proven on the host (`evaluate --json`
twice = timestamp only). The plan goldens needed no regeneration: `PlannedTransition`
carries no posture field, so schema version 1 stays for both schemas (deliberate: no
bump while field is serde-defaulted). `spec/contract-spec.md`'s data contract gained the
`posture_confidence` row in the same change.

Remaining work when resumed:

1. ~~Populate the field from `collect()`~~ — **done 2026-11-11/12, landed on main**:
   `20da5e6` wired `derive_posture_confidence` (`BputilOutcome::{RootReadParsed,
   RootReadUnparsed, RootReadUnavailable}` → Measured / UntrustedRead / UntrustedRead —
   a pass with no root read still earns UntrustedRead via the always-direct
   `csrutil` SSV read; `Unmeasured` stays the deserialisation floor), `6333c5c` made
   `diff()` compare it, and the live host re-proves it: `evaluate --json` twice differs
   only in `captured_at`, reporting `posture_confidence: UntrustedRead` +
   `security_mode: Unknown` without a cached sudo credential, exactly as designed. The
   coherence rule ("Measured over Unknown mode is rejected, not clamped") is enforced in
   `validate()`.
2. ~~Update every `BootState` literal and regenerate the plan goldens **deliberately**~~
   — done this step; goldens confirmed unaffected (`PlannedTransition` has no posture
   field).
3. ~~Update `spec/contract-spec.md`'s data-contract section~~ — done this step.
4. ~~Cross-container posture fields (rank 1's second half)~~ — **done 2026-11-12**
   (`feat/other-container-posture`): `OtherContainer` gained `posture_confidence`
   (same serde default honesty), `collect()` attempts one non-interactive
   `sudo -n bputil -d -v <uuid>` per other container with the same
   fresh-derivation mapping as the target read (`other_container_posture` — measured
   only from that call's own outcome; failures degrade to `Unknown` + `UntrustedRead`
   via the pass's always-present direct `csrutil` signal), successes recorded into
   `evidence.raw_outputs`, and `validate()` now enforces the Measured/Unknown coherence
   rule per container. The earlier "multiply the sudo gamble" objection is superseded
   in `extract_other_container_uuids`'s replacement docs. This single-VG host
   exercises the empty branch live (`other_containers: []`, twice-run gate holds); the
   populated branch is unit-covered.
