# 00 — Threat model and scope

## Assets (what we're protecting / what matters if it breaks)

| Asset | Where | Why it matters |
|---|---|---|
| `SecurityMode` / `Environment` classification | `src/env.rs`, `src/state/collect.rs` | Every downstream decision (`plan()`'s legality check, the future `is_mutation_allowed()` gate) is only as trustworthy as these two values. A bug here is a *logic* vulnerability, not a memory-safety one, but it's the highest-value target in the whole codebase. |
| IMG4 manifest parser | `src/state/img4.rs` | Parses bytes this binary didn't produce. Classic memory-safety/DoS surface. Not yet wired into production, which is exactly why it's cheap to fuzz now. |
| `BootState` deserialization (`verify --baseline`) | `src/main.rs::cmd_verify` | Parses a JSON file the user points the tool at — may not be self-produced (e.g. shared between machines, fetched by automation). |
| The audited subprocess wrapper's invariant ("only `wrapper.rs` spawns a process") | `scripts/ci_guards.sh` | The entire safety case for `apply`/`revert` in P3+ depends on every subprocess call being observable. A gap here is a gap in the whole project's auditability, not just a theoretical one. |
| This host machine | N/A — it's not part of the tool at all | Explicitly out of scope to modify per the root `CLAUDE.md`. Every plan in this folder treats "the host" as a constraint, not a target. |

## In scope for `vuln_res/` agents

- `bputil-eval`'s own Rust source (`src/`), its test fixtures, and `scripts/ci_guards.sh`.
- The dependency graph pinned in `Cargo.lock` (SBOM/CVE scanning only — not patching
  upstream crates ourselves unless a fix is trivial and well-tested).
- Reading (not attacking) the real firmware files under `../research/26B7124__MacOS/` and
  the IPSW's own metadata (`../research/BuildManifest.json`, `ipsw_file_listing.txt`) —
  strictly as structural reference for fuzz-corpus realism (e.g. confirming IM4P/IM4M
  byte-layout assumptions), never as something we try to find a *usable* bug in.
- A disposable VM or container this user owns, as the execution sandbox for fuzzing —
  never the host itself. See `03-sandboxed-execution-environment.md`.

## Explicitly out of scope (same list as `../CLAUDE.md`, restated here because a threat
model document is where people actually check this before starting new work)

- The Boot ROM, SEP, iBoot, or any Apple signature-verification implementation, as a
  *target* — not as something we try to find exploitable bugs in, even using the real
  firmware images already present in this repo.
- Any device this user doesn't own, or any VM/container modeling one at scale.
- Owner-credential handling of any kind.
- The host machine itself, beyond reversible, repo-scoped actions.

## Priority order (why these plans are sequenced this way)

1. **Static analysis first** (`01`) because it's the cheapest signal — no campaign to run,
   no sandbox to build, and it directly operationalizes the brittle-parsing and CI-guard
   findings already written up in `AUDIT.md` §2–3.
2. **Fuzzing second** (`02`) because the two best targets (`img4.rs`, `cmd_verify`'s
   deserialization) are already identified and already pure functions — no new product
   code needs to exist first.
3. **Sandbox before running anything at scale** (`03`) — a fuzz campaign run unboxed on
   the host is itself the kind of host-impact the root `CLAUDE.md` asks to avoid (sustained
   CPU/disk use, crash artifacts littering the repo). Get the container/VM right before
   running a long campaign, not after.
4. **Triage/minimization and disclosure/fix last** (`04`, `05`) because they consume the
   first three stages' output — there's nothing to triage until something's been found.

## Exit gate for this plan

A short written list (this file) of what's in and out of scope, agreed before any fuzz
harness or static-analysis agent is built — so that "be creative" in finding bugs never
quietly becomes "be creative about what counts as in scope."
