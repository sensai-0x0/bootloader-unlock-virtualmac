# Project 1 — Continuous Fuzz Bug Hunter

**One-line pitch:** turn the already-designed, never-executed `vuln_res/` fuzzing
pipeline (plans 02–05) into a real scheduled cadence against this repo's own parsers —
the literal "live bug hunter" the brief asks for, scoped entirely to code this project
owns.

## APT-mindset framing

An APT hunting for a foothold doesn't fuzz a target once — it runs sustained, patient
pressure against the target's parsers (the code that has to accept bytes it didn't
produce) for as long as it takes to find the one memory-safety bug that's worth weaponizing,
then it sits on that bug until it's useful. The defensive inversion is direct: run that
same patient, continuous pressure against **our own** parsers — `state/img4.rs`'s DER
decode and `main.rs::cmd_verify`'s `BootState` deserialization, both of which accept bytes
this binary didn't produce — before anyone else gets the chance, inside a sandbox, on a
schedule, with automatic scoring of what's worth a human's time first.

## What's reused from this repo today

- `.claude/agents/vulnres-fuzz-harness.md` — scaffolds the two `cargo-fuzz` targets and
  seed corpora. Already specced (`vuln_res/plans/02-fuzzing-harness-agent.md`), never run.
- `.claude/agents/vulnres-environment-runner.md` — the only agent allowed to execute
  anything, and only inside a registered disposable environment
  (`vuln_res/knowledge/environments/`, currently empty).
- `.claude/agents/vulnres-triage.md` — the reachability × memory-safety-weight ×
  blast-radius scoring rubric (`vuln_res/plans/README.md`'s "quickly evaluating
  vulnerabilities" section), already proven repeatedly on static-analysis findings: it's
  the exact rubric that scored and closed `ssv-enabled-contains-whole-blob` and
  `security-mode-full-contains-whole-blob` (both 9/9, both fixed) across the two static
  sweeps run so far — this project is about pointing that same proven rubric at fuzzer
  output for the first time, not inventing a new one.
- `.claude/agents/vulnres-disclosure.md` — the three-outcome model (our code / upstream /
  escalate), so a found bug doesn't just sit in a findings file.
- `vulnres-reporting` (skill) — cadence rollups to `reports/{daily,weekly,monthly}/`.
- `vuln_res/sweep-reports/` and `vuln_res/knowledge/` — the stores already built to hold
  this project's output; nothing new needs inventing here.

## Architecture (prose)

`vuln_res/plans/06-orchestration-and-scheduling.md`'s trigger model already specifies the
right cadence split — this project is mostly *executing* that plan, not designing a new
one:

1. **Scaffold once:** run `vulnres-fuzz-harness` to build `fuzz/fuzz_targets/img4_decode.rs`
   and `fuzz/fuzz_targets/boot_state_deserialize.rs`, seeded from
   `tests/fixtures/image4_apticket.der` and this repo's own committed `evaluate --json`
   outputs — never from the real firmware under `research/26B7124__MacOS/`, which stays
   structural-reference-only per `vuln_res/CLAUDE.md`.
2. **First bounded run, manual, approved:** `vulnres-environment-runner` creates one
   disposable container (plan 03's default — pure Rust parsers need no macOS, so a
   container beats a VM here), runs each target for minutes, not hours, copies any crash
   artifacts out, tears the container down.
3. **Triage and close the loop once:** `vulnres-triage` scores whatever came back (even
   "nothing crashed" is a valid, recordable result); `vulnres-disclosure` resolves any
   real finding into a PR, exactly like the `ssv-enabled-contains-whole-blob` precedent.
4. **Only after step 3 closes cleanly once**, propose a recurring cadence (weekly is the
   plan's own suggestion) — each recurrence still goes through the same environment-approval
   gate per run, it does not become automatic just because a prior run was approved.
5. **Reporting:** `vulnres-reporting` rolls up what ran and what was found, on the same
   cadence.

## Guardrail mapping

| Guardrail | How this project respects it |
|---|---|
| No execution outside a registered disposable environment | Every campaign goes through `vulnres-environment-runner`'s existing hard rule — no exception for "it's just a scheduled run now." |
| No new host-level footprint without asking | `cargo fuzz` is not installed on this host today — `vulnres-fuzz-harness` already asks before installing it; this project doesn't bypass that. |
| Scope stays on owned code | Both fuzz targets are this repo's own parsing functions; corpus seeding explicitly excludes the real firmware as an attack target (`vuln_res/CLAUDE.md`, `vulnres-fuzz-harness`'s "what you never do"). |
| Human review before merge | `vulnres-disclosure` opens PRs, never merges them — unchanged by this project. |
| Reachability/`SecurityMode` as the asset that matters most | Already encoded in the scoring rubric (`00-threat-model-and-scope.md`'s asset table) — this project doesn't need to redefine priority, just execute against it. |

## Phased build order

1. Scaffold the two fuzz targets + corpora (`vulnres-fuzz-harness`, with `cargo fuzz`
   install approval requested first).
2. One manual, approved, bounded campaign in a fresh disposable container.
3. Triage → disclosure, closing one full finding-to-resolution cycle (or confirming a
   clean run) — this is `vuln_res/plans/06`'s own exit gate for the whole suite, and this
   project is how it finally gets met.
4. Propose a recurring cadence explicitly, with the user approving the schedule itself as
   a separate decision from approving any individual run.
5. Wire `vulnres-reporting` for the cadence rollup.

## Open risks / what needs sign-off before any code runs

- Installing `cargo fuzz` — new host tooling, ask first (step 1).
- Creating the first disposable container — ask first, per the environment registry's own
  rule (step 2).
- **Making the cadence recurring at all** is its own sign-off, separate from approving any
  single run — a standing schedule is a different risk profile than a one-off campaign,
  and should be asked for explicitly once step 3 proves the pipeline works, not assumed
  as the natural next step.
- Corpus realism depends on structural-only use of the real firmware already in
  `research/` — any future seed-corpus change should be checked against that boundary
  again, not just inherited from this proposal.

## Success metric

One bounded fuzz run per target (e.g. 10 minutes) completes end-to-end — either clean, or
producing a fuzzer-confirmed finding that `vulnres-triage` scores and `vulnres-disclosure`
resolves to a PR — closing the loop this suite has been designed for but never executed,
the same "ran once and actually worked" bar the root project applied to its own P1 exit
gate.
