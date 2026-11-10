---
title: Theme C — budget-weighted gap ranking
source_document: archive/tool-analysis-offensive-threat-intel-defence.md (§6)
parent: tool-analysis-parent.md
role: agent (evaluator agent)
status: complete
completed_at: 2026-11-11
deliverable: reports/evaluator/gaps-roadmap-2026-11-11.md
---

# Gaps roadmap — rank what bounds the intelligence capability, cheapest-first

**Input:** the confirmed/reputed claims from `high-offensive.md`'s deliverable. If a
capability audit refuted something, do not spend budget ranking around a false premise.

**Your job:** source §8.2 — a **budget-weighted ordering** of the §6 gaps as they gate
a threat-intelligence-defence productisation, cheapest "unlocks the most" first.

---

## Parent task B1 — decompose the nine gaps (source §6)

Child tasks:

- [x] **B1.1** For each gap below, write a one-paragraph restatement in your own words,
      grounded in what the capability audit confirmed about the current code:

      1. No temporal layer / baseline store (`verify` diffs one ad-hoc JSON; no
         scheduling, alerting, history)
      2. Single-host ceiling (no enrollment list, no SSH runner, no fleet view;
         `projects/03-fleet-drift-watch/PROPOSAL.md` specifies this unbuilt)
      3. No CTI interoperability (no STIX 2.1/TAXII, no ATT&CK-style tagging, no
         IOC consumption/emission)
      4. Coverage gaps inside the measurement: IMG4 parser not wired into
         `state::collect` (blocked on `bputil -d -j` / confirmed manifest path,
         `plans/phase-1.md` item 1); `other_containers[].security_mode` hardcoded
         `Unknown`; `security_mode` degrades to `Unknown` without sudo with no
         posture-confidence field; no downgrade/rollback observables in the schema
      5. Mutating half intentionally nonexistent (`authorize`/`execute`/`verify`
         invariant assertion are P3 stubs)
      6. Evidence anti-tamper hash-only (no signature, key custody, or
         transparency-log append; `projects/products/01-attestation-bundle/` design
         unbuilt)
      7. No confidence telemetry (`env::detect()` relies on `bputil -d` OS Type
         strings acknowledged inconsistent across builds, per `src/env.rs`)
      8. No intel-feedback loop (pattern analysis is per-sweep, not continuous)
      9. Hardware generativity (fixtures cover one host; no chip-generation matrix —
         the P5 gate's problem)

- [x] **B1.2** For each gap, record **its live cost today**: which of source §5's five
      strengths it caps (e.g. gap 1 + 2 cap "Diff-as-detection" at a manual two-step
      run; gap 3 caps all intel value at repo-edge markdown).

## Parent task B2 — score and order

Child tasks:

- [x] **B2.1** Score each gap on three axes the owner can audit —
      *cost to close* (engineering effort, hardware risk, and any human-in-1TR
      dependency from `plans/phase-3.md`+), *capability unlocked* (which pipeline
      role from source §7 moves from hypothesis to working), and
      *guardrail exposure* (`threat-intel-defence.md` will formally stress-test
      these; here, just flag any gap whose obvious fix touches the 1TR gate or a
      golden rule).
- [x] **B2.2** Produce the ordered list, cheapest-unlocks-most first. Explicitly
      evaluate the source's prior hypothesis (§6 preamble of §8.2) as candidate
      #1: *a fleet/baseline/scheduling layer — the drift-watch proposal — converts
      the existing proven read-only measurement into a real detection capability
      with zero new hardware risk.* Confirm or refute it from
      `projects/03-fleet-drift-watch/PROPOSAL.md`, not from the hypothesis itself.
- [x] **B2.3** For each ranked item, name the *gate it unlocks* in the phased plan
      (`spec/phased-plan.md`) — e.g. the IMG4 wiring is literally phase-1 item 1 —
      so the order aligns with, or deliberately diverges from, the existing phase
      sequence, with the reason stated.

## Parent task B3 — interleave with existing plans

Child tasks:

- [x] **B3.1** Cross-reference `plans/README.md`: for each ranked gap, note whether an
      existing phase, proposal, or tracking file already covers it (`phase-1.md`
      item for IMG4; drift-watch proposal for gaps 1–2; attestation-bundle proposal
      for gap 6; `research-environment.md` / `extension-local-model-hosting.md` for
      hardware-adjacent gaps). Mark each as *spec exists unbuilt* or *no spec exists*.
- [x] **B3.2** Identify any ranked item that conflicts with an existing phase
      ordering or golden rule, and state the conflict precisely.

---

## Deliverable

Write `reports/evaluator/gaps-roadmap-<YYYY-MM-DD>.md` containing:

1. The nine decomposed gap paragraphs with today's live cost.
2. The scoring table (cost / capability unlocked / guardrail exposure) with the
   scoring rationale visible.
3. The **ordered cheapest-first list** with a one-line "why this rank" per item and
   the explicit verdict on the drift-watch-as-#1 hypothesis.
4. The B3.1 coverage cross-reference table.

Constraints: read-only analysis; no code changes; guardrails from
`tool-analysis-parent.md` §5 bind any suggestion you make.

**Handoff:** your ordered list is the candidate work stream that
`threat-intel-defence.md` stress-tests against the guardrails, and
`evaluator-decisions.md` converts into build-next / research-next / don't-build.
