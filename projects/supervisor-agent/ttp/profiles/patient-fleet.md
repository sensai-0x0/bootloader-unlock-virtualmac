# Profile: patient-fleet

**Class modeled:** Salt Typhoon / G1045-class (telecom-infrastructure-concentration,
long-dwell). Per BUILD-SPEC §5.3 item 1.

## Skill level
High — nation-state-affiliated, infrastructure-focused tradecraft.

## Patience
Very high. "Detection delay is the attacker's friend" is this profile's organizing
principle: it prefers techniques whose detection latency, under this portfolio's
*current, real* state, is longest — not necessarily the most damaging technique in
the abstract. A probe that returns a short detection latency is deprioritized even
if it's otherwise attractive.

## Primary interest
1. **Fleet drift invisibility** — project 3's territory (`fleet-enrollments:first-list`
   clock, `state='never'`: zero enrolled Macs exist yet, so there is nothing to drift
   *and* nothing watching for it — the honest double-absence this profile is built to
   exploit).
2. **Valid-accounts persistence** (T1078 and sub-techniques) — once a fleet exists,
   this profile prefers blending into legitimate owner credentials over any
   exploit-driven foothold, matching the real Salt Typhoon playbook (long-dwell via
   living-off-the-land, not novel malware).

## Phase vector
`init/recon -> persist/expand -> persist/expand -> triage-learn -> persist/report`
(JSON: `["init_recon","persist_expand","persist_expand","triage_learn","persist_report"]`)
— two full `persist/expand` cycles before this profile ever considers itself ready for
anything else, reflecting its patience.

## Technique preferences per phase (drawn from mapped TTPs, §5.4 step 1)
- `init_recon`: techniques under the Reconnaissance/Resource Development tactics that
  the fused state shows as genuinely open (no capability/clock defending them).
- `persist_expand`: **T1021.004** (Remote Services: SSH) over an enrolled fleet Mac —
  this portfolio's own worked example (BUILD-SPEC §5.4 step 3). **T1078** (Valid
  Accounts) once an enrollment list exists. **T1222** (File and Directory Permissions
  Modification) against the bputil-eval boot-security surface this portfolio's own
  `vm_sec_research` track is built to measure — attested-usage caveat: no `G1045`
  (Salt Typhoon) `technique_groups` row names T1222 specifically as of v20.1 ingest;
  preferred here on the profile's own stated interest (boot-security-state tampering
  fits a telecom-infrastructure actor's concentration goal), not attested group usage
  — this is `sim_steps.basis = 'unattested_preference: ...'` per §3.3 item 4, a caveat
  row, not a silent assumption.
- `triage_learn`: whichever technique's gap probe returned the longest detection
  latency in the prior phase — the profile invests where it was blindest.
- `persist_report`: C2-adjacent techniques only if a prior phase's probe found a live
  outbound channel this portfolio doesn't watch; otherwise skipped (nothing to prefer).

## Stop conditions
- A gap probe returns `detect_via` naming a *live* (not `never`/`invalid`) clock with a
  sub-24h staleness policy — the profile treats that as "found the tripwire," retreats
  to recon, and the scenario's next phase reverts to `init_recon`.
- Three consecutive steps all resolve `covered` — the profile concludes this surface is
  genuinely watched and moves its *next scenario* to a different surface (not modeled
  within one scenario; recorded as a `sim_outcomes.summary` recommendation for the next
  seeded run).

## Expected honest gap (today's real state)
`fleet-enrollments:first-list` is `state='never'` with **zero** `fleet_enrollments`
rows — a patient adversary on an unmonitored enrolled Mac has a detection latency of
**∞** under current state, exactly as BUILD-SPEC §8 phase 5's accept criterion (c)
names. This is a state fact this portfolio's own schema already records, not a
dramatization.
