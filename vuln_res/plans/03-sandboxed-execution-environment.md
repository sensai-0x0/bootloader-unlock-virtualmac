# 03 — Sandboxed execution environment

Where fuzz campaigns, and any future "evaluate a virtual environment" work, actually run.
This plan exists because of one constraint that overrides convenience: **the host this
session runs on is never a target, and a long-running fuzz campaign (hours of 100% CPU on
one core, a growing corpus directory, crash artifacts) is exactly the kind of lasting
footprint the root `CLAUDE.md` says to avoid without explicit sign-off.**

## Why not just run `cargo fuzz run` directly on the host

It would work, technically. It's also:
- A sustained resource commitment (hours of CPU) the user hasn't explicitly authorized for
  this specific run.
- A growing `fuzz/corpus/` and `fuzz/artifacts/` directory that's new, lasting repo state
  if left uncleaned.
- Harder to bound — if a target's crash handler ever did something unexpected (it
  shouldn't, for a pure-function target, but "shouldn't" is exactly the kind of assumption
  a sandbox exists to not have to rely on).

## Options, cheapest first

1. **A disposable container** (Docker/OrbStack, whichever is already on this machine —
   check before installing anything new) with the repo mounted read-only except for
   `fuzz/corpus` and `fuzz/artifacts`, CPU/memory capped, network disabled. This is the
   right default for fuzzing pure Rust parsing code — there's no real reason to need a
   full VM for this, since the targets have no OS-level dependencies (no `bputil`, no
   Apple-specific tooling at all — `img4`/`der`/`serde_json` are pure Rust).
2. **The disposable VM already built for the `progress/goal.md` track** (`tart`-managed,
   per `plans/research-environment.md`) could also host a campaign, but that VM's whole
   purpose is simulating real macOS boot-security behavior — using it as a generic fuzzing
   sandbox would conflate two different research tracks for no benefit, since the fuzz
   targets don't need macOS at all. Prefer option 1; only reach for a VM if a future fuzz
   target genuinely needs macOS-specific behavior (none currently do).
3. **A remote/cloud sandbox** (an `isolation: "worktree"` or `isolation: "remote"` agent
   run, if available) if local container tooling isn't present and the user would rather
   not install it locally at all.

Whichever is chosen, get explicit user sign-off before creating it — this is exactly the
"environment is the thing you act on" case the root `CLAUDE.md` describes as the right
pattern, as opposed to installing fuzzing infrastructure directly on the host.

## What runs inside

- `cargo fuzz run <target> -max_total_time=<N>` for a bounded duration (start with
  minutes, not hours — extend only once the pipeline downstream of it, triage and
  minimization, is proven to work on whatever it finds).
- Nothing network-facing, nothing that reads outside the mounted repo subset, nothing that
  writes outside `fuzz/corpus`/`fuzz/artifacts`.

## Evaluating virtual environments (the other half of this plan's name)

Separately from fuzzing: if a future task is literally "evaluate this VM/firmware image
for structural issues" (e.g. does the disposable-VM track's IPSW/VM setup have any
obviously wrong permissions, exposed services, or stale credentials baked in) — that's a
**configuration/hygiene audit of a sandbox we built ourselves**, same category as the
static-analysis agent in `01`, just pointed at VM config instead of Rust source. It is
not vulnerability research against Apple's platform security running inside that VM. Keep
those two things labeled differently even when they happen to use the same VM.

## Exit gate

A container (or approved alternative) exists, is resource-capped, network-disabled, and
has successfully run both fuzz targets from `02` for a short bounded duration with results
written only to the mounted corpus/artifacts paths — nothing touching the host outside the
container, and no lasting host footprint after the container is torn down.
