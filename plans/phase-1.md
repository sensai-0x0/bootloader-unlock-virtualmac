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
