---
title: Theme B — threat-intelligence defence mapping + guardrail stress-test
source_document: archive/tool-analysis-offensive-threat-intel-defence.md (§5, §7, §9)
parent: tool-analysis-parent.md
role: agent (evaluator agent)
status: complete
completed_at: 2026-11-11
deliverable: reports/evaluator/threat-intel-defence-2026-11-11.md
---

# Threat-intel-defence — critique the CTI mapping, stress-test every proposal

**Your job:** two of the source §8 deliverables live in this theme — the critique of
the §7 CTI/detect pipeline mapping, and the §8.4 **guardrail stress-test**. You run
after `high-offensive.md` (ground truth) and alongside/after `gaps-roadmap.md`
(candidate ideas to stress-test).

---

## Parent task C1 — critique the CTI pipeline mapping (source §5, §7)

Child tasks:

- [x] **C1.1** Validate the §5 strengths against your A-task verdicts: the audited
      wrapper + hash-chained bundle + validity predicate as the trustworthy
      measurement primitive; `BootState` as a compact IOC schema for boot-chain
      weakening; `state::diff.rs` as the drift-detection primitive; fail-closed
      culture as a security property; the proven vuln_res obverse capability. For
      each: does the claimed CTI role survive the audit? (e.g. hash-only evidence
      proves internal consistency, not authorship — does "evidence you can trust"
      survive that caveat unqualified?)
- [x] **C1.2** For each pipeline-role row in the §7 table
      (Collection / Normalisation / Detection / Evidence / Adversary-strategy
      awareness / Response), state whether the mapped primitive is
      *live*, *partial*, or *hypothesis* — citing the audit.
- [x] **C1.3** Validate the technique-coverage suggestion against the current
      ATT&CK matrix (defence-impairment via SSV/SIP weakening ~ Impair Defenses;
      kext persistence ~ Kernel Modules and Extensions; bootkit-class persistence ~
      Pre-OS Boot): confirm technique IDs are current, and flag where the indicator
      set derived from `BootState` does not actually cover what those techniques
      imply (e.g. no downgrade/rollback observables in the schema — gap from §6.4).
- [x] **C1.4** Confirm the legal/defensibility framing: the tool detects the
      *resulting configuration* and must not become an exploitation or bypass
      instrument (golden rules §2, §6; refusal conditions in root `CLAUDE.md`).
      Quote where each boundary document is actually anchored.

## Parent task C2 — guardrail stress-test (source §8.4)

For **every** proposal that survives into the `gaps-roadmap.md` ranked list, plus
every proposal in `projects/*/PROPOSAL.md` touched by that list, run these child
tasks:

- [x] **C2.1** For each proposal, answer: is it achievable **without** loosening any
      golden rule (`spec/build-spec.md`), any CI guard (`scripts/ci_guards.sh`), or
      the no-mutation-without-1TR gate? Cite the specific rule tested.
- [x] **C2.2** Flag any proposal that requires loosening them — mark it explicitly
      **"don't build as proposed"** and, where a compliant variant exists, propose the
      variant (e.g. a fleet runner that fans out read-only `evaluate` calls needs no
      1TR loosening; a builder that weakens posture remotely would — state which and
      why).
- [x] **C2.3** Check honesty-of-state implications: for each proposal, does it ever
      produce a claim about state without a fresh measurement (§9's "evidence
      honesty")? Baseline stores and alerting surfaces are the high-risk items here.
- [x] **C2.4** Check the scope boundary: does any proposal point the vuln_res-style
      adversarial machinery at anything other than this toolchain's own code and
      dependency tree? `vulnres-pattern-analysis` is scope-checked so generic
      technique knowledge is kept and anything target-specific to Apple's platform
      is discarded — verify the same scoping survives in each proposal.

---

## Deliverable

Write `reports/evaluator/threat-intel-defence-<YYYY-MM-DD>.md` containing:

1. The §5 strengths critique with surviving/qualified/refuted verdicts.
2. The §7 mapping table re-rendered with live / partial / hypothesis per row.
3. The ATT&CK technique-validation result with gaps called out.
4. The **guardrail stress-test table**: one row per proposal —
   *proposal → passes without loosening? → which guardrail binds → compliant variant
   or "don't build as proposed"*.

Constraints: read-only analysis; no code changes; the §9 constraints in
`tool-analysis-parent.md` §5 are the very thing you are stress-testing — do not
recommend exceptions to them under any pressure.

**Handoff:** the compliant-variant column feeds `evaluator-decisions.md` directly —
only items with a green pass or a named compliant variant may become "build next".
