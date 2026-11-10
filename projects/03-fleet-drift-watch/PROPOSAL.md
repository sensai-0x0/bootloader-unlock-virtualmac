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

## Phases 1–2 specification (drafted 2026-11-11, per evaluator Build-next rank 2)

`reports/evaluator/evaluator-decisions-2026-11-11.md` routes this project's first two
steps through an acknowledge-flow-first spec, before any baseline format is written.
That ordering is deliberate: the acknowledgment step is both the false-positive control
and the project's primary attack surface, so it gets designed first.

### Scheme 1 — acknowledgment flow (the part that must exist first)

Rules, in order of bindingness:

1. **An alert never becomes a baseline.** The diff that raised the alert is a finding,
   not an accepted fact. Closing an alert and updating a baseline are the same human
   action only when taken explicitly and in one direction.
2. **An acknowledgment always requires a fresh measurement.** The runner takes a new
   `evaluate --json` at acknowledgment time and validates the asserted change still
   matches that fresh diff. Accepting from the alert's own evidence is prohibited — a
   stale acknowledge would let post-alert drift through unobserved (the honesty-of-state
   guardrail, applied to the runner, not just the tool).
3. **Every acknowledgment carries a reason.** A free-text, owner-typed reason is stored
   with the ack; an ack without a reason is malformed and refused. The reason is what
   makes a fleet audit readable later ("SSV change was mine, 1TR round-trip test") and
   what makes an attacker's silent-ack path conspicuous.
4. **Acks are append-only and hash-chained.** Ack records are never edited or removed;
   the chain is verifiable the same way `report.json`/`report.sha256` bundles already
   are (`report.rs`'s format, reused — no new crypto, just the existing sha256-chaining
   discipline).
5. **Manual, not networked.** Acknowledgment happens on the runner by the same human who
   would resolve the alert in a briefing; there is no remote-ack API to design, harden,
   or accidentally expose.

### Scheme 2 — baseline store format

One directory per enrolled Mac under a repo-local store (no server, no database; the
same flat-files-as-schema reasoning `vuln_res/sweep-reports/` uses):

```
drift-watch/
  enrollments.json          ← the explicit, by-hand list; no discovery, ever
  state/
    <enrollment-name>/
      baseline.json         ← last-known-good posture (the alert comparator)
      baseline.sha256       ← chain head, verified on every run
      acks.json             ← append-only ack log (chain-linked to baseline.json)
      acks.sha256
```

- `enrollments.json` — array of `{ name, target, added_by, added_at, approved_by, note }`;
  `approved_by` must be a person (the per-fleet opt-in rule at each new enrollment); the
  runner refuses entries it can't positively validate against this file.
- `baseline.json` — fields: `schema_version`, `enrollment_name`, `last_known_good`
  (a `BootState` captured verbatim by a real `evaluate --json` run),
  `source_evidence` (`report_dir`, `report_sha256`, optional `acked_at_acks_position`),
  and `diff_source`. `last_known_good` is a real `BootState` (never a hand-typed
  summary) so `state/diff.rs` consumes it with zero adapter code.
- `acks.json` — array of `{ id, accepted_at, accepted_by, reason, fresh_state_captured_at,
  fresh_evidence_ref, diff: [DiffEntry…] }`, hash-chained across files exactly like the
  report bundles. Editing or truncating this file breaks the chain and is itself an alert.
- The alert comparator is always: fresh `evaluate --json` vs `baseline.json`'s
  `last_known_good`, via the existing `state::diff::diff()` — no new diffing logic exists
  in this project, by design.

### Scheme 3 — downgrade/rollback observables (rank 3, lands with rank 2)

An attacker's cheapest move isn't flipping a mode — it's *reverting* to an older,
weaker-but-known-good-looking state, or rolling the runner's own view back. The baseline
store makes rollback visible by treating versions as first-class diff fields:

1. **Every stored and fresh state carries the versions it was produced under** — the
   tool's own `schema_version`, the baseline store's format `schema_version` (distinct
   number; bumped whenever a field here changes), and the `evaluate` binary version that
   captured it. These are ordinary serialized fields, so `state::diff::diff()` surfaces
   any mismatch as a normal `DiffEntry` — no special-casing in the comparator.
2. **A downgrade is an alert, not an ack shortcut.** A fresh run reporting an *older*
   tool schema/binary version than the baseline's is alertable even when every posture
   field is identical — "the same posture measured by an older tool" is exactly what a
   rolled-back or tampered runner looks like. Acknowledging it follows the same Scheme 1
   flow with an explicit reason; there is no auto-accept for version regressions.
3. **Format bump discipline:** downgrading the *store format* is refusal, not alert —
   a runner that reads a `baseline.json` with a newer store `schema_version` than it
   understands fails closed with a clear error rather than guessing at unknown fields
   (the same forward-compat rule the tool's own `SCHEMA_VERSION` gate already enforces
   on bundles).
4. **Twice-run gate re-proof:** rank 3's binding guardrail is that the P1 twice-run gate
   still holds — the version fields are constant across two back-to-back runs on an
   unchanged machine, so the goldens' only allowed delta remains `captured_at`. The
   `bputil-eval` `schema_version` bump this new state-field makes is regenerated
   deliberately, the same documented-shape-change discipline the posture-confidence
   merge used.

### Failure modes the format is designed against

| Failure | Counter in the spec |
|---|---|
| A real drift re-baselines itself into invisibility | Rule 1 (alert ≠ baseline) + Rule 2 (fresh measure at ack) |
| Runner's SSH key compromised → blanket-mute the fleet | Rule 3 (per-ack human reasons) + acks.json chain audit: an ack with no corresponding alert, or one blanket-ack across many Macs, is reviewable as an anomaly |
| False positives burn the operator out | Rule 5 + a distinct ack.reason convention documented for "planned change" vs "explained change" — TODO in phase 3 once scheduling exists |
| Baseline file tampered with directly | `baseline.sha256`/`acks.sha256` chain: a runner that fails chain verification alerts instead of comparing, and never falls back to silently rebuilding a baseline |

### Exit gate for phases 1–2

One enrolled test Mac: introduce a deliberate drift (flip via Apple's own `bputil`, with
the usual human-in-1TR rules for anything mutating — see `spec/phased-plan.md`'s P3 gate),
confirm the alert fires from a fresh `evaluate --json`, acknowledge it with a reason,
confirm the ack lands in `acks.json` with the chain extending, re-run the comparator —
and confirm the identical run the next day produces **no** diff and no alert without
another acknowledgment in between. Scheduling (phase 3) does not start until this gate
closes.

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
