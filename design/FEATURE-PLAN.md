# Dashboard feature plan — contracts to components

This plan extends the design system in `design/` (see `README.md` and
`components.md`) from vuln_res/'s sweep-and-findings surface to bputil-eval's
own evaluator/control surface, grounded in `spec/contract-spec.md`'s exact
field and operation contracts. It is a plan only — no new views are built
here, no wiring to real data.

## The two contract surfaces

| Surface | Source of truth | Covered today |
|---|---|---|
| vuln_res/ sweep & findings | `vuln_res/sweep-reports/TEMPLATE-finding.md`, `findings-index.md` | `view-1-sweep-findings.html`, `view-2-campaign-overview.html` |
| bputil-eval evaluator/control | `spec/contract-spec.md` — `BootState`, `PlannedTransition`, `Report` | Not yet designed — this plan |

## The governing principle: "no buttons" is the contract, not just the aesthetic

`ReadOnlyUnlessGated` (contract-spec.md, global invariants) requires that no
mutating command runs unless `environment == OneTrueRecovery` and a live,
*interactive, typed* owner confirmation was recorded. `authorize.confirm`'s
contract is explicit: it **MUST NOT be satisfiable non-interactively, by a
stored token, or by an agent.** A dashboard is, by construction, exactly the
kind of thing that MUST NOT be able to satisfy it.

So for this surface, "no buttons" isn't a style preference carried over from
the vuln_res views — it's a hard requirement. Nothing in this plan ever
proposes an "Apply" or "Revert" control, a credential field, or any
automated path to one. Everything below is `evaluate` / `plan` (dry-run) /
`verify` / `report` — the four operations the contract spec says can never
return exit 10, because they never need 1TR.

## Feature set

| Feature | Contract source | Reuses | New component |
|---|---|---|---|
| Posture ledger | `BootState` (§ Data contracts) | `.manifest` header, `.ledger`/`<details>` rows | Posture-confidence tick, security-mode tick |
| Boot-object ledger | `BootState.enrolled_objects[]`, `.other_containers[]` | `.ledger` rows, `.detail` dl | — |
| Mode-transition rail | `SecurityMode` state machine (CLAUDE.md's modeled edges) | `.stage-rule` (ported from the campaign view) | — |
| Plan preview | `PlannedTransition` | `.ledger` row, `.status[escalated-to-human]` tick | — |
| Evidence/report viewer | `Report` | `.ledger` rows (`diff[]`), invariants tick | Invariants checklist row |
| Cross-reference | vuln_res finding `target` naming a bputil-eval symbol | `.detail dl` — just a convention, no new markup | — |

### Posture ledger — `BootState`

A `.manifest` header carrying `captured_at`, `environment`, `host.chip` /
`host.macos_build` / `host.serial_masked` (already masked to its last 4
characters at the data layer — the view never has the full serial to leak).
Below it, two ledger sections:

- **Target container** — one row: `security_mode`, `ssv_enabled`,
  `allows_custom_kernel`, `allows_third_party_kexts`, rendered as a single
  expandable row (there is exactly one target container by definition).
- **Enrolled objects / other containers** — one `.ledger` row per
  `enrolled_objects[]` entry (`role`, `signer`, truncated `sha384`) and per
  `other_containers[]` entry, each expandable to the full hash and raw
  fields, same mechanics as a vuln_res finding row.

No headline-figure hero here — unlike a sweep, a single `BootState` has no
natural "one tally" to lead with (the closest analog, `security_mode`
itself, is categorical, not a count), so this view opens straight into the
manifest. Forcing a hero number here would be exactly the generic "big
number by default" trap the original design pass called out — right to
reject it on the vuln_res views, right to reject it here too.

### Mode-transition rail — the `SecurityMode` state machine

The campaign view's `.stage-rule` ruler (built for
recon→fuzz-harness→…→disclosure) ports directly: `Full ↔ ReducedKexts`,
`Full ↔ PermissiveCustomKernel`, current mode lit. Same component, new
labels — the kind of reuse the token/component system exists for.

### Plan preview — `PlannedTransition`

`plan()` is always read-only, even in macOS (contract-spec.md,
`plan(volume, target)`'s `ensures`). Its result renders as one `.ledger`
row: `from_mode → to_profile`, expandable to the full `commands[]` list in
`--font-data`. For any mutating `to_profile`, the row's status tick reads
`escalated-to-human` with the amber tick and label "requires 1TR + owner
confirmation" — reusing the existing status vocabulary exactly as intended:
this is a human gate, the same semantic the vuln_res views already use it
for.

### Evidence/report viewer — `Report`

- `diff[]` → one `.ledger` row per changed field path, same expand-to-detail
  mechanics as a finding row (`before`/`after` in place of
  `reproduction`/`resolution`).
- `invariants[]` → a new **invariants checklist** row per global invariant
  (`ReadOnlyUnlessGated`, `SingleContainerTouched`, `Reversible`,
  `NoCredentialHandling`, `SupportedMechanismsOnly`, `MeasuredTruth`,
  `EvidenceComplete`, `OwnershipConfirmed`): `held == true` renders with the
  same filled-square tick as `status[open]`'s "good" sense reversed — here
  filled-green means *held*, and a violation renders with the
  `escalated-to-human` amber triangle, because that is exactly what
  contract-spec.md says happens to one: it "routes the finding to
  coordinated disclosure," i.e. escalates to a human. No retry affordance —
  consistent with "invariant violations are findings, not retryable errors"
  (CLAUDE.md's non-negotiable constraint list).
- `evidence_bundle_path` → shown as a plain monospace path, same
  reveal-don't-download convention `components.md` already specifies for a
  finding's PoC path.
- `exit_code` → the one place this view gets a headline figure, and only
  when non-zero: a bad exit code is the single dominant fact a report needs
  to lead with, same "paper bulletin leads with one tally" justification
  used on the vuln_res views, now for the bad-news case instead of a count.

### Cross-reference: vuln_res findings ↔ evaluator contracts

Several real finding slugs already name bputil-eval symbols directly
(`state::collect::parse_security_mode`, `state::validate`). No new
component — just a convention for the `.detail dl`'s `target` row: when it
names a symbol this plan's posture/evidence views also surface, say so in
the same line, so the two surfaces read as one system rather than two
unrelated dashboards bolted together.

## New components to spec (before building)

1. **Posture-confidence tick** — `Measured | UntrustedRead | Unmeasured`,
   same visual grammar as the status tick (filled / outline / dash), new
   `data-status` values on the existing `.status` component — no new CSS
   mechanism needed, just new modifier rules.
2. **Security-mode tick** — `Full | Reduced | Permissive | Unknown`.
   `Full` reuses the filled-green "good" sense; `Reduced`/`Permissive` use
   the neutral `paper-white-dim` dash — they are valid, owner-chosen states,
   not problems, so they must not borrow amber's "needs a human" meaning;
   `Unknown` also uses the neutral dash, matching `false-positive`'s "no
   claim is being made" sense, not amber — an `Unknown` mode is a measurement
   gap, not an escalation, per `MeasuredTruth`'s honesty requirement.
3. **Invariants checklist row** — binary held/violated, reusing the
   `open`/`escalated-to-human` tick pair as described above.

## Explicit non-goals

Carried over from `spec/build-spec.md`'s refusal conditions and this plan's
own governing principle — never design, even as a mockup:

- An "Apply" or "Revert" control, or anything that looks like one.
- A credential field of any kind.
- Any control that could be satisfied non-interactively or by an agent.
- A live connection to a real device's boot state (this plan, like the
  views it extends, stays static/sample-data until a separate decision is
  made to wire it up).
