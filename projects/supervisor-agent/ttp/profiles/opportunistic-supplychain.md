# Profile: opportunistic-supplychain

**Class modeled:** T1195.001-era supply-chain adversary — doesn't pick a target, waits
in the dependency path for whoever pulls the poisoned artifact. Per BUILD-SPEC §5.3
item 2. T1195.001 ("Compromise Software Dependencies and Development Tools") was
promoted to v2.0 in ATT&CK v20.1 — confirmed against the real MITRE release notes
during this phase's build, not assumed — making it the single most pointed technique
for a repo whose own staleness infrastructure watches `Cargo.lock` by name.

## Skill level
Medium. This class of actor doesn't need novel tradecraft — just patience at scale and
one successfully-poisoned dependency.

## Patience
Opportunistic, not infinite: waits for *a* target to pull the dependency, not for one
specific target to become reachable. Within a single simulated scenario this reads as
"always ready," since the adversary's clock runs on the ecosystem's update cadence, not
this portfolio's.

## Primary interest
Build-time trust and fixture/provenance grooming: anywhere this portfolio accepts
content it didn't produce without re-verifying it — `Cargo.lock`/`Cargo.toml` changes,
vendored fixtures (`tests/fixtures/image4_apticket.der`, vendored from the `image4`
crate's own test suite per this repo's own documented provenance), and the
`vulnres-fuzz-harness`/`vulnres-environment-runner` capabilities that would eventually
pull in future dependencies.

## Phase vector
`init_recon -> execute -> triage_learn -> persist_report`
(JSON: `["init_recon","execute","triage_learn","persist_report"]`) — one pass; this
profile doesn't model a persistence phase because its "foothold" IS the dependency
itself, already persistent by construction once accepted.

## Technique preferences per phase
- `init_recon`: **T1195.001** (Compromise Software Dependencies and Development
  Tools) against this repo's own `Cargo.lock`/`Cargo.toml` — the exact surface
  `knowledge:cargo-audit-clean`'s staleness clock exists to watch.
- `execute`: **T1195.001** again, at the point a poisoned dependency would actually
  execute (via `cargo build`/`cargo test`, both of which this repo's own `scripts/
  ci_guards.sh` and CI run routinely) — or, if the fused state shows no fuzz/mutation
  harness built yet (`fuzz_targets` table empty, project 1 pre-build), **T1608.007**
  (Stage Capabilities: AI Result Poisoning) against a parsed knowledge/fixture file
  the supervisor itself ingests — this is the agent-directed profile's signature
  technique too, but legitimately dual-relevant here: a supply-chain actor grooming a
  *fixture* the supervisor parses is the same mechanism, different motive.
- `triage_learn`: whichever of the above resolved `uncovered`/`asserted_unproven` —
  invests in understanding why before moving to report.
- `persist_report`: no C2 modeled; this profile's "report" phase is the poisoned
  artifact quietly shipping downstream, which this simulation never generates or
  produces as a runnable artifact (hard boundary, §5.5) — recorded as a text-only gap
  probe about detection, not as a payload.

## Stop conditions
- A gap probe against `T1195.001` resolves `covered` with a *live* clock (`knowledge:
  cargo-audit-clean` or `knowledge:build-test-clean` both `state='live'`, not
  `invalid`/`never`) — the profile concludes dependency-path grooming is watched here
  and the scenario ends with `sim_outcomes.summary` recommending no further investment
  on this surface.
- `cargo-audit`/`cargo-deny` both reporting clean on a **current** (non-stale) run is
  the one state that would fully close this profile's primary interest; short of that,
  every probe stays open.

## Expected honest gap (today's real state)
Every `knowledge:*` staleness clock this profile's probes touch is currently
`state='invalid'` (real commits postdating the last asserted-clean claim) — a
dependency-path adversary operating right now would find a *stale*, not current,
clean bill of health on exactly the surfaces that matter most to it.
