---
title: Theme D — interoperability recommendation + decision request
source_document: archive/tool-analysis-offensive-threat-intel-defence.md (§8.3, §8.5)
parent: tool-analysis-parent.md
role: agent (evaluator agent)
status: complete
completed_at: 2026-11-11
deliverable: reports/evaluator/evaluator-decisions-2026-11-11.md
---

# Evaluator decisions — the owner-facing synthesis

This file runs **last**; it consumes the deliverables of the other three child files.
Nothing here may contradict a guardrail stress-test verdict from
`threat-intel-defence.md`.

---

## Parent task D1 — interoperability recommendation (source §8.3)

Child tasks:

- [x] **D1.1** Decide and argue: should intel emission be **STIX 2.1 first**, or an
      **internal delta/attestation format first**? Ground the argument in what the
      audit confirmed the tool already emits today (hash-chained `report.json`
      bundles) and what the gaps roadmap says is cheapest. Consider: commitment
      cost of STIX objects vs. the stability of an internal schema under active
      change (`schema_version` discipline in `src/state/mod.rs`), and whether STIX
      can be a *lossless later projection* of an internal format.
- [x] **D1.2** Decide and argue **where ATT&CK-style technique tagging belongs**:
      on finding templates (the vuln_res `sweep-reports/` side) vs. on `BootState`
      itself. Note the honest objection to tagging BootState directly
      (BootState is a *state schema*, not a finding; and the current indicator set's
      coverage is incomplete per `threat-intel-defence.md` C1.3).
- [x] **D1.3** State the IOC consumption/emission position, if any, that follows from
      D1.1 — or explicitly "not yet" with the trigger condition that would change it.

## Parent task D2 — decision request (source §8.5)

Child tasks:

- [x] **D2.1** Compile the candidate list from the gaps roadmap: only items whose
      guardrail stress-test verdict was a pass or a named compliant variant may
      appear.
- [x] **D2.2** Sort into exactly three buckets, each entry one line an owner can
      resolve without code changes:
      - **Build next** — start now; cite which existing phase/proposal it lands in
        (`plans/README.md` cross-reference from gaps-roadmap B3.1), or that no spec
        exists yet.
      - **Research next** — needs investigation before commitment; name the open
        question (e.g. IMG4-into-collect needs `bputil -d -j` output from a real
        host, or the manifest-path confirmation in `plans/phase-1.md` item 1).
      - **Don't build** — failed the guardrail stress-test, or the capability would
        only come at the cost of loosening a golden rule, a CI guard, or the 1TR
        gate. State which.
- [x] **D2.3** Verify the list is resolvable **without code changes** — every entry
      must be actionable as a document decision, a research task, or an assignment
      to an existing plan file. Re-read each entry and delete anything that implies
      unattended mutation of a real device (P3/P4 stay human-with-physical-access,
      per `plans/README.md`).
- [x] **D2.4** For each "Build next" entry, name the first concrete child task and the
      plan file it should be appended to, so the owner can delegate immediately.

## Parent task D3 — close out the pack

Child tasks:

- [x] **D3.1** Write the deliverable (below), then link all four
      `reports/evaluator/*` files from each other so the pack reads as one unit.
- [x] **D3.2** Update `plans/tool-analysis-parent.md` status frontmatter to
      `complete` (or `blocked` with reasons) and update the `plans/README.md` table
      so the pack is discoverable.
- [x] **D3.3** Note, in the deliverable's closing section, what changed in your
      assessment vs. the archived brief's own prior hypotheses — the owner reads
      the delta, not the restatement.

---

## Deliverable

Write `reports/evaluator/evaluator-decisions-<YYYY-MM-DD>.md` containing:

1. The interoperability argument with a one-paragraph decision and its refutable
   assumptions listed.
2. The **decision table**: bucket / item / first child task / destination plan file
   / binding guardrail (last column shows which §9 constraint or golden rule makes
   each "don't build" a don't).
3. The deltas-from-prior-hypotheses section.

Constraints: this synthesis is a document; it must not require or enable any
mutation outside the human-in-1TR rules, and every claim it carries must trace back
to one of the three prior deliverables or a cited source file.

**Handoff:** this deliverable is the pack's terminal output — the owner acts on this
file alone; the other three are its audit trail.
