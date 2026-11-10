# Project 3 — Fleet Boot-State Drift Watch

**One-line pitch:** schedule the already-proven, already-read-only `evaluate`/`verify`
pair across N owned, enrolled Macs to catch boot-security drift — a genuine
security-critical role (continuous compliance monitoring) that never goes near the
mutation boundary at all.

## APT-mindset framing

An APT that has compromised one machine in a fleet wants its foothold's boot-security
weakening — a `SecurityMode` change, SSV disabled, an unexpected boot object enrolled —
to go unnoticed across the rest of the fleet for as long as possible; detection delay is
the attacker's friend. The defensive inversion is the obvious one: build the thing that
notices immediately and everywhere this user has visibility, using measurement this
project has already proven stable (`evaluate` run twice differs only in timestamp — the
literal P1 exit gate) rather than inventing new detection logic.

## What's reused from this repo today

- `evaluate`/`verify`/`report` — P1 and P2 are done; this project adds a scheduling and
  fan-out layer on top, not new measurement logic.
- `state/diff.rs` — the structured `BootState` diff already used by `plan` and `verify`;
  this is exactly the drift-detection primitive this project needs, reused as-is.
- `report.rs`'s evidence bundle — each enrolled Mac's periodic measurement becomes its own
  hash-chained record, same format already proven in `evidence/vm-sec-research-25D125/`.
- The honesty-of-state discipline (golden rule 8) — a drift alert here means the same
  thing it means everywhere else in this project: a fresh measurement proved it, not an
  assumption.

## Architecture (prose)

A small, explicitly-maintained **enrollment list** (hostnames/SSH targets the user adds by
hand — never auto-discovered, never scanned for) is the only input that defines "the
fleet." On a schedule, a runner connects to each enrolled Mac over the user's own existing
SSH access, runs `bputil-eval evaluate --json` remotely, and diffs the result against that
Mac's last-known-good baseline using the same `state/diff.rs` logic `verify` already uses.
Any change to `security_mode`, `ssv_enabled`, or enrolled boot objects that the user hasn't
separately marked as an expected, tracked change raises an alert with the fresh evidence
attached. Baselines update only when the user explicitly acknowledges a change as
expected — never silently, which would let a real drift re-baseline itself into invisibility.

## Guardrail mapping

| Guardrail | How this project respects it |
|---|---|
| No remote/at-scale operation against devices without a present human owner (golden rule 6 / root `CLAUDE.md`) | Every enrolled Mac is one this user explicitly owns/manages and added by hand to the enrollment list — no auto-discovery, no scanning of unknown hosts, ever. This is the proposal in this whole portfolio closest to that line, and the enrollment-by-hand requirement is the thing that keeps it on the right side of it. |
| `ReadOnlyUnlessGated` | This project never calls `apply`/`revert` — it has no mutation code path to gate in the first place, by construction, not by discipline alone. |
| `NoCredentialHandling` | SSH access reuses the user's own existing fleet-management credentials/keys — this project never stores, generates, or automates OS-level owner credentials, and doesn't need to, since it never attempts a mutation. |
| Honesty of state | An alert is only ever raised from a fresh `evaluate --json` result, never cached or inferred — same discipline `verify` already enforces for a single target. |

## Phased build order

1. **Enrollment file format + one test Mac:** a simple, explicit list format (no
   discovery), `evaluate`-over-SSH against exactly one machine the user names.
2. **Diff-against-baseline alerting:** reuse `state/diff.rs` as-is; add the
   "acknowledge as expected" step so legitimate changes don't become permanent false
   positives.
3. **Explicit, opt-in scheduling:** never silently "at scale" — the schedule itself is a
   separate ask from approving the enrollment list, same split as project 1's cadence.
4. **Rollup reporting:** lean on `vulnres-reporting`'s cadence pattern rather than
   building a second reporting mechanism from scratch.

## Open risks / what needs sign-off before any code runs

- **This is the closest any proposal in this portfolio comes to "remote operation at
  scale,"** and needs the clearest, most explicit per-fleet opt-in of all six — re-asked
  every time the enrollment list grows, not assumed to extend automatically.
- **False-positive risk:** a legitimate 1TR change made through normal means, without the
  tool knowing about it in advance, will look identical to a real compromise unless the
  "mark as expected" acknowledgment step is built before scheduling goes live, not after.
- **SSH credential scope:** this project is only as safe as the user's own existing fleet
  SSH access already is — it adds no new secret handling, but it does mean a compromise of
  the *runner's* own SSH key would be a real fleet-wide exposure; that's an operational
  risk to flag explicitly to the user before enrollment, not something this proposal can
  design away.

## Success metric

A deliberately-introduced test drift (manually flipping one enrolled test Mac to `Reduced`
via normal `bputil`, exactly like the M6/M9 manual proof already in this repo) is detected
and reported within one scheduled cycle, with zero false positives across a full week of
otherwise-unchanged enrolled machines.
