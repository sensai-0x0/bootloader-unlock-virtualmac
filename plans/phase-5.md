# Phase 5 — Hardening and release: not started

Needs `phase-3.md` and `phase-4.md` fully done first. This phase is mostly about breadth
(more hardware, more adversarial input) rather than new capability, so it's the most
parallelisable across people/time of the three remaining phases.

## 1. Hardware matrix coverage

`spec/phased-plan.md` wants at least one base chip per generation in scope (M1–M5), a
Pro/Max for the multi-die cases, each on supported macOS builds, each with its own scratch
container. Concretely, for each additional machine you get access to:
1. Run `cargo test` on it — the fixture-driven tests in `src/state/collect.rs` and
   `src/state/img4.rs` should pass unchanged (they don't depend on chip generation).
2. Capture its own redacted fixtures (same process as `plans/phase-0.md` item 2 and
   `tests/fixtures/README.md`'s redaction steps) and add them to `tests/fixtures/`, named
   by chip (e.g. `bputil_display_policy_M1_REDACTED.txt`).
3. Run `phase-3.md`'s full round trip and `phase-4.md`'s Permissive round trip on a scratch
   container on that machine. If any flag or output format differs (the risk
   `spec/phased-plan.md` specifically calls out — "bputil/kmutil flags drift across macOS
   builds"), fix the parser to handle it and add a test from that machine's real output,
   never a guessed one. On a genuinely unsupported host, return exit 14
   (`UnsupportedHost`) — never a guessed command, per that same risk mitigation.

## 2. Fuzzing

Fuzz three surfaces, per `spec/phased-plan.md`:
- `src/state/img4.rs`'s `parse_manifest_der` — malformed DER input. `cargo-fuzz` with
  `der`-shaped corpus seeds (start from the real fixture added in `phase-0.md` item 1 and
  mutate it).
- The `bputil -d` / `csrutil status` text parsers in `src/state/collect.rs`
  (`parse_security_mode`, `extract_serial_masked`, `extract_volume_group`) — these already
  degrade to `Unknown`/`None` on unrecognised input by design; fuzzing here is about
  confirming they never panic, not about finding new valid inputs.
- Whatever JSON deserialisation path exists for `BootState`/`PlannedTransition`/`Report`
  (`serde_json::from_str` is already exercised by `cmd_verify` in `src/main.rs`) — fuzz
  malformed JSON against it.

## 3. Reproducible, signed evidence bundle

`src/report.rs`'s `write_bundle` currently writes `report.json` + `report.sha256` (a single
hash, not yet a hash *chain* across multiple bundle entries, and not yet signed). Extend it:
- Hash-chain multiple raw captures if a session produces more of them than
  `BootState.evidence.raw_outputs` already holds (this becomes relevant once `phase-3.md`'s
  `execute`/`verify` start producing before/after pairs with their own raw outputs).
- Sign the final bundle hash with a release key; ship a small standalone verifier (a
  separate tiny binary or a `--verify-bundle` subcommand) that only needs the bundle
  directory and the public key, no access to the original device.

## 4. Documentation and disclosure policy

- Man page / `--help` text completeness check (clap already generates `--help`; review it
  reads clearly to someone who hasn't read the specs).
- An operator guide, written from `phase-3.md`/`phase-4.md`'s actual round-trip steps once
  they're proven, not from the spec in the abstract.
- The coordinated-disclosure path for an exit-13 finding (`spec/build-spec.md`'s refusal
  table: "verify reports an invariant violation -> Halt; preserve evidence; recommend
  revert; route to coordinated disclosure"). This needs a real contact path to Apple
  decided before it's needed, not improvised during an actual finding.

## 5. Release

Versioning (`Cargo.toml`'s `version` is still `0.1.0`), binary signing, and a distribution
channel. `spec/phased-plan.md` tags the P1 evaluator alone as a plausible first independent
release (v0.1) "useful on its own, independent of any unlock capability" — worth
considering shipping that *before* P3–P5 are done, rather than waiting for the full tool.

## Exit criteria

- [ ] Coverage across the hardware matrix you actually have access to (note which chip
      generations remain untested in `tests/fixtures/README.md` rather than claiming full
      coverage you don't have).
- [ ] Fuzzing clean within whatever time budget you set, logged in the repo.
- [ ] The reproducible bundle independently verified by someone other than whoever
      generated it.
- [ ] Documentation complete, including the disclosure path.
