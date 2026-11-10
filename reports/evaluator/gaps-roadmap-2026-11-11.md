---
title: "Deliverable 2 — budget-weighted gap ranking (§6 → cheapest-unlocks-most)"
child_plan: plans/gaps-roadmap.md
parent: plans/tool-analysis-parent.md
date: 2026-11-11
input_deliverable: reports/evaluator/high-offensive-2026-11-11.md (capability audit — all §6 gap claims re-confirmed)
---

# Gaps roadmap — ranking

Scores use Low / Med / High. Cost includes engineering effort, hardware/1TR dependency,
and research unknowns. "Unlocks" refers to the §7 CTI pipeline roles (Collection,
Normalisation, Detection, Evidence, Adversary-awareness, Response). Guardrail exposure
is a flag, not a verdict — `threat-intel-defence.md` formally stress-tests each.

## B1 — the nine gaps, restated with live cost

1. **No temporal layer / baseline store.** `verify`/`cmd_verify` diffs one ad-hoc JSON
   (`src/main.rs:35` cap aside). Live cost today: detection is a manual two-step run;
   `state::diff.rs` sits idle as a standing capability. Cost to close: **Low–Med**
   (persistent baseline dir + acknowledge-as-expected flow + scheduling hook; no new
   measurement logic).
2. **Single-host ceiling.** No enrollment, SSH runner, fleet view. Cost to close:
   **Med** — the full design exists (`projects/03-fleet-drift-watch/PROPOSAL.md`:
   enrollment-by-hand list, evaluate-over-SSH, diff-as-is, rollup via
   `vulnres-reporting` cadence). Carries the portfolio's largest operational surface
   (runner SSH-key compromise = fleet-wide exposure, per the proposal's own risk line).
3. **No CTI interoperability.** Intel value dies at repo-edge markdown. Cost to close:
   **Med** — an internal delta/attestation emission first (candidate projection to
   STIX 2.1 later) is additive; no existing spec.
4. **Coverage gaps inside the measurement.**
   - *IMG4 not wired into collect* — confirmed again this audit (zero `img4` refs in
     `src/state/collect.rs`; `vuln_res/AUDIT.md` §1.1 notes the `dead_code` cfg's).
     Cost: **code Low, but gated on Research** (`plans/phase-1.md` item 1: find out
     whether `bputil -d -j` exposes hashes/signers before any raw IM4M path guessing).
     Unlocks `enrolled_objects` — the persistence-evidence half of the IOC schema —
     which is currently always empty.
   - *`other_containers[].security_mode` hardcoded `Unknown`* — `src/state/collect.rs:195`,
     documented at `:173`. Cost: **Low**.
   - *Silent Unknown degradation, no posture-confidence field* — `collect.rs:12,228-259`;
     a consumer cannot distinguish measured-Full from unmeasured. Cost: **Low**.
   - *No downgrade/rollback observables* — schema additions (`schema_version` bump),
     Med; partially arrives free via the IMG4 work (boot-object version deltas).
5. **Mutating half intentionally nonexistent.** P3/P4 stubs; only useful for
   AIxCC-style impact loops. Cost: **High by design** — human-in-1TR is the feature,
   not the cost. Not a detection-productisation gate; deliberately excluded from
   build-next ranking below.
6. **Evidence anti-tamper hash-only.** Full design exists unbuilt
   (`projects/products/01-attestation-bundle/PROPOSAL.md`). Cost: **Med**. Unlocks
   third-party-verifiable Evidence.
7. **No confidence telemetry.** `env::detect()` two-signal reality confirmed
   (`src/env.rs:54-60,113`). Cost: **Low for the field, but meaningful data needs the
   fleet layer (2) or hardware matrix (9)** — effectively rides along.
8. **No intel-feedback loop.** Pattern analysis is per-sweep
   (`vulnres-pattern-analysis`); continuous priorisation is unbuilt cadence
   machinery (`vuln_res/plans/06-orchestration-and-scheduling.md` touches it). Cost:
   **Med–High**, and it only pays once structured findings exist (after 4 and 6).
9. **Hardware generativity.** One host's fixtures; the P5 gate's problem. Cost:
   **High** (matrix or simulated M6-generation host — `plans/research-environment.md`
   covers the IPSW path). Cheap pre-cursor: the simulation plan, which is its own
   research item.

## B2 — scoring table and order

| Gap (or slice) | Cost | Capability unlocked | Guardrail exposure flag |
|---|---|---|---|
| 4b posture-confidence + 4c other_containers + 7 field | Low | Detection fidelity (trust in every other unlock) | baseline-confusion risk none; honest-Unknown surfaced rather than hidden |
| 1 temporal/baseline store (single host) | Low–Med | Detection manual → standing | stale-baseline re-baselining risk (drift-watch step-2 acknowledge flow is the guard) |
| 4a IMG4 wiring | Low + Research gate | IOC schema completeness (`enrolled_objects`) | none — read-only; path-guessing danger is handled by the phase-1 protocol |
| 2 fleet fan-out (drift-watch steps 1,3,4) | Med | Collection + Detection at scale | per-fleet opt-in mandatory; runner SSH-key exposure; no mutation path by construction |
| 6 attestation bundle | Med | Evidence third-party-verifiable | key custody decisions; design proposal exists |
| 3 CTI interop (internal-delta first, STIX projection) | Med | makes 1–4 externally consumable | none |
| 4d downgrade/rollback observables | Med | richer indicators (`~Pre-OS Boot` depth) | schema migration care (`schema_version`, twice-run gate retest) |
| 7 confidence telemetry (full) | Low code / High data | Detection trust at scale | none |
| 8 intel-feedback loop | Med–High | prioritised collection | none direct |
| 9 hardware generativity (martix / IPSW sim) | High | generalisation evidence | none; P5 gate territory |
| 5 mutation half | High | Response role (§7), AIxCC-style impact proof | maximal — human-in-1TR phases only |

**Ordered list (cheapest-unlocks-most first):**

1. **Posture-confidence + cross-container posture fields (4b, 4c, thin 7).** Smallest
   diff in the codebase with the largest honesty payoff: a consumer stops being unable
   to tell "measured Full" from "unmeasured."
2. **Persistent baseline store + single-host drift alerting (gap 1 = drift-watch step
   2, locally).** Converts the proven `evaluate`/`diff` pair into a standing detection
   capability on the same hardware already in hand — zero new hardware risk.
3. **Baseline-driven downgrade/rollback observables (4d).** Once 2 exists, version
   deltas become detectable for free — schema additions riding an existing mechanism.
4. **Fleet fan-out (gap 2 = drift-watch steps 1, 3, 4).** The big unlock: detection
   everywhere this owner has visibility. Explicit per-fleet opt-in required, re-asked
   on every enrollment change (the proposal's own rule).
5. **IMG4 research then wiring (4a).** Split intentionally: *research next* first
   (`bputil -d -j` question), *build next* after. Unlocks the persistence half of the
   indicator set.
6. **Attestation bundle (6).** Evidence stops being self-attested.
7. **Internal delta format emission, STIX 2.1 as a later projection (3).** Ordered
   after 6 because the delta format's natural container is the attestation bundle.
8. **Full confidence telemetry (7).** Rides fleet data from 4.
9. **Intel-feedback loop (8).** After structured findings exist.
10. **Hardware generativity (9).** P5-gated; `research-environment.md` as the
    research pre-cursor.
11. **Mutation half (5).** P3/P4, human-with-physical-access — not ranked for the
    agent; the §7 Response role arrives there or not at all.

**Verdict on the source's prior hypothesis** (fleet/baseline/scheduling as #1):
**confirmed with one amendment.** The audit confirms the measurement, diff, and
evidence primitives are all live and reusable as-is (`high-offensive-…md` A2/A3), and
the drift-watch proposal is real, scoped, and guardrail-mapped — but the *cheapest*
first slice is the **local** one: baseline store + single-host alerting before any SSH
fan-out, plus the near-trivial posture-confidence fields in front of both.

## B3 — coverage cross-reference (what already has a spec)

| Ranked item | Existing spec? | Where |
|---|---|---|
| Fleet fan-out, scheduling, rollup | **exists, unbuilt** | `projects/03-fleet-drift-watch/PROPOSAL.md` (incl. guardrail mapping + phased order) |
| Temporal/baseline store (steps 1–2, single host) | partial — drift-watch's phase-for-one-host | same proposal, steps 1–2 |
| IMG4 wiring | **exists** | `plans/phase-1.md` item 1 (with the -j-first protocol); parser fixture bereits proven (`tests/fixtures/image4_apticket.der`) |
| Attestation | **exists** | `projects/products/01-attestation-bundle/PROPOSAL.md` |
| CTI emission / tagging | none | decided in `evaluator-decisions.md` (D1) |
| Posture-confidence / other_containers / version observables | none (CLAUDE.md documents the Unknown hardcode as deliberate) | new child tasks needed |
| Mutation half | **exists, human-scoped** | `spec/phased-plan.md` P3/P4; `plans/phase-3.md`, `plans/phase-4.md` |
| Intel-feedback loop | partial | `vuln_res/plans/06-orchestration-and-scheduling.md` |
| Hardware matrix / generativity | **exists** | `spec/phased-plan.md` P5; `plans/research-environment.md` (IPSW simulation) |

**Conflicts with existing plans:** none found. One dependency to preserve: the
drift-watch proposal itself demands the "acknowledge-as-expected" step be built
**before** scheduling goes live — rank 2 (baseline store) must ship that flow, not
defer it.

**Handoff:** ranked items 1–4, 6 and their guardrail flags go to
`threat-intel-defence.md` (C2 stress-test); the interop question to
`evaluator-decisions.md` (D1) — this deliverable only ranks, it does not decide the
STIX-vs-internal question.
