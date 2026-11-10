---
title: Evaluator pack — parent orchestrator
source_document: archive/tool-analysis-offensive-threat-intel-defence.md (processed + archived 2026-11-11)
role: agent (evaluator agent, per source §8)
status: pending
child_files:
  - high-offensive.md
  - threat-intel-defence.md
  - gaps-roadmap.md
  - evaluator-decisions.md
---

# Evaluator pack — parent orchestrator

You are the *evaluator agent* defined in §8 of the archived analysis document. This
file is the parent: it tells you what to do, in what order, and how to know you are
done. The four child files each carry one theme of the source analysis, decomposed
into parent tasks and child tasks. Work them **in the order below**; later files
consume outputs of earlier ones.

---

## 1. Mission

Produce a defensible evaluation of `bputil-eval` as an offensive-informed
threat-intelligence defence tool: confirm or refute its claims, rank its gaps,
recommend an interoperability posture, stress-test every proposal against the
non-negotiable guardrails, and hand the owner a build-next / research-next /
don't-build decision list. **No code changes** — your outputs are documents.

## 2. Required reading (before any task)

1. `archive/tool-analysis-offensive-threat-intel-defence.md` (sections 1–9)
2. `../README.md` (repo overview)
3. `../CLAUDE.md` (what is implemented vs deliberately open)
4. `../vuln_res/CLAUDE.md`
5. `../spec/build-spec.md`, `../spec/contract-spec.md`, `../spec/phased-plan.md`
6. `../projects/03-fleet-drift-watch/PROPOSAL.md` and the other `projects/*/PROPOSAL.md`

## 3. Execution order and file map

| Order | File | Theme | Feeds |
|---|---|---|---|
| 1 | [high-offensive.md](high-offensive.md) | What the tool + vuln_res suite actually are; capability audit against source | threats… all later files |
| 2 | [gaps-roadmap.md](gaps-roadmap.md) | Budget-weighted gap ranking from confirmed reality | evaluator-decisions.md |
| 3 | [threat-intel-defence.md](threat-intel-defence.md) | CTI mapping critique + guardrail stress-test of every proposal | evaluator-decisions.md |
| 4 | [evaluator-decisions.md](evaluator-decisions.md) | Interop recommendation + final decision request to the owner | the owner |

## 4. Output contract

- Every child file ends with a **Deliverable** section stating the exact artifact to
  produce and where to write it.
- Deliverables live under `reports/`, named
  `evaluator/<child-file-stem>-<YYYY-MM-DD>.md` (create folders as needed).
- Cite: for every confirm/refute claim, cite file + line or test name. No unsourced
  assertions.

## 5. Global constraints (bind every child file, non-negotiable)

These are source §9 and survive the pivot untouched:

- Read-only by default; mutation only via Apple's own tools, only in confirmed 1TR,
  only with a present human owner typing credentials. No credential handling anywhere.
- No bypass of, or fault-injection into, Boot ROM/SEP/iBoot/signature paths — not on
  real devices, not in VMs, not on extracted firmware.
- Findings resembling Apple-enforcement gaps are disclosure items, never capabilities.
- Execution happens in registered disposable environments, per-action approved; the
  session host stays unmodified.
- Evidence honesty: fresh measurement or it isn't a claim.

If any proposed enhancement requires loosening a golden rule, a CI guard
(`scripts/ci_guards.sh`), or the no-mutation-without-1TR gate, you must **flag it as
such and mark it "don't build as proposed"** — do not soften the guard to fit the idea.

## 6. Completion criteria (parent)

- [ ] All four child files' child-task checklists are fully checked or explicitly
      blocked with a reason.
- [ ] All four deliverables exist under `reports/evaluator/`.
- [ ] `evaluator-decisions.md` has produced a final decision list the owner can act
      on without code changes.
- [ ] This parent file's `status:` frontmatter is updated to `complete` (or `blocked`
      with reasons) and `plans/README.md` table rows reflect reality.
