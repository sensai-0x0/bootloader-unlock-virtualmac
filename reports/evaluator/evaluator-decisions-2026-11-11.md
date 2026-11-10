---
title: "Deliverable 4 — interoperability recommendation + decision request (+ pack close-out)"
child_plan: plans/evaluator-decisions.md
parent: plans/tool-analysis-parent.md
date: 2026-11-11
linked_deliverables:
  - ../evaluator/high-offensive-2026-11-11.md
  - ../evaluator/gaps-roadmap-2026-11-11.md
  - ../evaluator/threat-intel-defence-2026-11-11.md
---

# Evaluator decisions — the owner-facing synthesis

*(This file links the other three deliverables; together they are the pack's audit
trail. The owner acts on this file alone.)*

## D1 — interoperability recommendation (source §8.3)

**1. Internal delta/attestation format first; STIX 2.1 as a later lossless projection
— not STIX-first.**

Argument: the tool already emits a hash-chained, self-verifying internal bundle
(`report.json`+`.sha256`, format proven and immutably honoured by the twice-run gate).
Inventing an internal delta object extends a schema that already has change-control
discipline (`SCHEMA_VERSION`, goldens), while STIX-first would force the tool to commit
to external object semantics while its own indicator set is still under-determined —
the capability audit and the ATT&CK validation both show fidelity gaps (empty
`enrolled_objects`, confidence fields) that would be frozen into propagating objects.
The guardrail stress-test also attaches a scrubbing condition to any emission: internal
format keeps that decision local until it's settled. Refutable assumptions: (a) that the
internal schema's churn will slow enough post-4d to make lossless projection cheap — if
instead churn stays high, revisit; (b) that projected STIX can carry squad-level nuance
(boot objects, container disjunction) — test the projection on one finding before
committing.

**2. ATT&CK-style tagging belongs on finding/drift templates (the reporting side), not
on `BootState` itself.**

`BootState` is a *state schema*; techniques are *claims about adversary behaviour*, and
tagging it would entangle Apple-semantic fields (SSV, AuxKC) with a matrix that changes
on a different cadence (v20 just introduced T1685). Template-side tagging keeps the
matrix version as report metadata, lets the same state carry different coverage tags as
the matrix evolves, and matches the vuln_res finding-template convention (one file per
finding, indexable). Refutable assumption: that template-side selection is enough to
express multi-technique drift — if a single drift event genuinely spans several
techniques, the template needs a technique array, not a scalar.

**3. IOC consumption/emission: explicitly "not yet."** Trigger to revisit: the fleet
layer (rank 4) ingesting a third-party indicator source (e.g. widely-shared known-bad
boot-object digests) — at that point consumption changes from opinion to capability.

## D2 — decision request (resolve without code changes)

Only stress-test-passed items appear; conditions carried from
`threat-intel-defence-2026-11-11.md`.

| Bucket | Item | First concrete child task | Destination plan file | Binding guardrail |
|---|---|---|---|---|
| **Build next** | Posture-confidence + cross-container posture fields (rank 1) | define the confidence enum (measured/untrusted-read/unmeasured) and its unit tests before touching `collect` | `plans/phase-1.md` (follow-ups section — it is explicitly P1-strengthening territory) | honesty of state — must surface unmeasured louder |
| **Build next** | Baseline store + single-host drift alerting (rank 2, condition attached) | author the acknowledge-as-expected flow spec *first*, then the baseline file format (drift-watch steps 1–2, one test Mac) | `projects/03-fleet-drift-watch/PROPOSAL.md` phased order steps 1–2 | evidence-honesty: alert only from fresh `evaluate`; no re-baselining |
| **Build next** | Downgrade/rollback observables (rank 3, lands with rank 2) | add version-delta fields + `schema_version` bump + re-run the twice-run goldens | same drift-watch file, step-2 scope | P1 twice-run gate must hold |
| **Research next** | IMG4-into-collect enabler: does `bputil -d -j` expose hashes/signers? (rank 5 gate) | run the probe on an owned disposable VM, per-action approved, record findings in `vuln_res/knowledge/` | `plans/phase-1.md` item 1 (its own step-2 protocol) | no FS-path guessing at local-policy storage; archive-doc discipline |
| **Research next** | ATT&CK v20 drift check: T1562 vs T1685 absorption, at ship time of first tags | re-run the mapping check when the first template lands | reporting-side: `reports/evaluator/…` follow-up note in whichever template file is created | — |
| **Research next** | Hardware-matrix pre-cursor via IPSW simulation (rank 10) | read/validate `plans/research-environment.md`'s sim steps against current IPSW availability | `plans/research-environment.md` | disposable-environment rule only |
| **Don't build** | STIX-first emission (rank 7 as "emission now") | — (already amended to internal-first; deferral is the decision) | revisit after ranks 1–2 ship and one template exists | scrubbing condition + under-determined fidelity would be frozen into externals |
| **Don't build** | Any automated/remote mutation, including AIxCC-style impact pipelines that automate owner credentials | — | mutation work stays human-with-physical-access: `plans/phase-3.md`, `plans/phase-4.md` | golden rule 4; the 1TR gate; §9 |
| **Don't build** | Auto-discovered/scanned fleet enrollment | — | enrollment stays by-hand (drift-watch's own proposal rule) | golden rule 1; per-fleet opt-in |

## D3 — pack close-out

- All four `reports/evaluator/*` files cross-linked (see this file's frontmatter; the
  other three cite the pack files they consumed).
- Parent `plans/tool-analysis-parent.md` status → `complete` (updated in its own
  commit below); `plans/README.md` already lists the five pack files.
- Deltas vs the archived brief's prior hypotheses: **(1)** the drift-watch-as-#1
  hypothesis is confirmed but sliced — local baseline alerting precedes any SSH
  fan-out, and posture-confidence outranks both; **(2)** CTI-interop was framed as a
  ranked gap; the decision later than rank 2: emission is deferred behind fidelity
  fixes and an internal-first format; **(3)** the brief's "evaluator produces a build
  list" is delivered with conditions attached rather than as unconditional green
  lights — the honest version of the same conclusion.
