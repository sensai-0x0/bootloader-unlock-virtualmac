# Extension Plan — Local-Model-Hosting Relevance for `bputil-eval`

**Companion to:** `reports/m2-bootloader-unlock-technicians-guide.md`
**Plan date:** 2026-11-10
**Status:** Proposed — not started. Nothing in this plan authorizes work ahead of `spec/phased-plan.md`'s existing gates; it extends the project along a new axis (hobbyist-relevant documentation), self-contained within this repository. It does not reorder or skip phases.

**Scope boundary:** this plan is scoped entirely to `the-ant-experiment` (this repository). It does not reference, link to, depend on, or propose any connection — code, documentation, or otherwise — with any other folder or project. Any future request to add such a link is out of scope for this plan and would need to be raised and decided separately.

## 0. Why this plan exists

`the-ant-experiment` builds a read-only-by-default, owner-gated tool for Apple's own `SecurityMode` spectrum. Some hobbyists who self-host local models also want driver- or kernel-level hardware access (a third-party kext, or a custom kernel) that `Full` security doesn't permit. Right now there is no single place, *within this repository*, documenting which classes of modification actually require `Reduced` or `Permissive` security, how risky they are, or what state this project's own tooling is in to help evaluate them safely. This plan builds that place, in stages, without ever getting ahead of what `bputil-eval` itself can actually prove, and without creating any dependency on or reference to work outside this repository.

## 1. Guiding constraint: this plan inherits every golden rule unchanged

Nothing here adds capability beyond what `spec/build-spec.md` already permits. Explicitly, this plan:

- Does **not** propose any mutation logic beyond what P3/P4 already specify.
- Does **not** propose remote, scripted, or unattended `SecurityMode` changes for any hosting use case — 1TR + physical owner presence remains mandatory for every workstream below.
- Does **not** create any link — code, documentation, or configuration — between this repository and any other folder or project. Every workstream's deliverables live entirely inside `the-ant-experiment`.
- Does **not** propose vetting, distributing, or recommending specific third-party kexts or custom kernels. Where a workstream below mentions a hobbyist use case (e.g., a kext-dependent driver), it documents the *security-mode prerequisite* for that class of use case, never a specific unsigned binary to trust.
- Treats a finding that something can't be done safely (e.g., the VM chip-generation blocker already found) as a legitimate deliverable, exactly as `reports/disposable-vm.md` and `reports/unlocked-bootloader-evidence.md` already do.

## 2. Workstreams

### A. Finish the M2-generation VM research already in progress (unblocked today)

**What:** Complete `progress/milestones.md` M8/M9 — a VM built from an IPSW matching this host's own chip generation (M2 Pro) or older, then test whether `bputil`'s SEP/LocalPolicy-dependent mutation path works inside it.

**Why it's first:** it's already in progress, it's the most direct answer to `progress/goal.md`'s open question, and — per `reports/m2-bootloader-unlock-technicians-guide.md` §3 — the M2 generation specifically is the easiest one to test on this exact host, since the chip-generation constraint only blocks *newer*-than-host targets.

**Exit gate:** either (a) a confirmed, fresh-measured `evaluate → plan → apply → verify` round trip inside the VM, reported per `progress/goal.md`'s four-step evidence chain, or (b) a clearly written finding that SEP/LocalPolicy communication fails inside the VZ guest, with a decision recorded on whether to pursue `spec/phased-plan.md` P3's real-scratch-hardware route instead. No work in workstream B starts until one of these two outcomes is recorded in `progress/milestones.md`.

**Owner:** human with access to this (or an equivalent M2-generation) host; this is VM-only work, no physical device risk.

### B. Build the P3 mutation pipeline against whichever target A proves viable

**What:** Implement `authorize`/`execute`/`verify`'s actual logic (currently doc-comment stubs — `reports/build-product.md` §6), scoped exactly to `spec/build-spec.md`'s per-module contracts, proven via the `full → reduced → full` round trip on the target workstream A validated.

**Why it's gated on A:** `spec/phased-plan.md`'s P2→P3 gate requires a disposable scratch target to exist and be proven *before* any mutation code is written — this project's own stated reason for not having started P3 yet (`reports/build-product.md` §6). This workstream does not relax that gate; it depends on A closing it.

**Exit gate:** `spec/build-spec.md`'s "Definition of done, per phase" phase-3 criteria — full round trip verified, negative tests (`apply` outside 1TR → exit 10, executor rejects an argv not in the plan, wrong post-state caught as exit 13) all passing.

**Owner:** human with physical access to the chosen scratch target, present for the 1TR credential step — same constraint `plans/phase-3.md` already documents for real hardware, extended to a VM target if A validates one.

### C. Document hobbyist-relevant `SecurityMode` profiles — documentation only, gated on B

**What:** A new reference document (`reports/hobbyist-profiles.md`, not yet written) cataloguing, for each `SecurityMode`, the *class* of hobbyist hardware/OS modification it's a prerequisite for — grounded in what Apple's own documentation says `Reduced`/`Permissive` actually unlock, not in any specific third-party kext or kernel this project evaluates or endorses. Two concrete classes already have solid public grounding and are the obvious starting entries:

1. **`Reduced` + third-party kexts** — legacy or specialty hardware drivers that predate Apple's modern DriverKit/system-extension model.
2. **`Permissive` + custom kernel** — the security-mode prerequisite the Asahi Linux project documents for running a non-Apple kernel on Apple Silicon hardware (cited publicly by that project; this plan does not re-derive or verify Asahi's own claims, only notes the `SecurityMode` precondition is real and documented by Apple independently).

**Why gated on B, not A:** writing hobbyist-facing guidance about what a transition *actually involves in practice* should be informed by this project's own completed round trip (B), not written ahead of having ever executed one. Until B lands, `reports/m2-bootloader-unlock-technicians-guide.md` already covers the honest, current state — this workstream supersedes it once there's real execution evidence to draw from.

**Exit gate:** the document exists, every claim in it traces to either Apple's own documentation or this project's own verified evidence bundles (no claim without a citation — the same standard `plans/research-environment.md` held itself to throughout), and it's reviewed for golden-rule compliance (no specific unsigned binary recommended, no performance claim made).

### D. Governance check — re-run before shipping any of the above

Before any workstream above is marked done, re-check it against:

- `spec/build-spec.md`'s "Out of scope and prohibited" list — nothing proposed here crosses it.
- The host-impact policy in this repo's `CLAUDE.md` — any new tooling installed for workstream A/B (e.g., continuing to use `tart`/`ipsw`) should be disclosed the same way `reports/disposable-vm.md` §4 already discloses the current installs, and the outstanding cleanup question there should be resolved (kept or removed, with the user's explicit decision) before this plan is considered complete, not left open indefinitely alongside a growing set of new host changes.

## 3. Sequencing summary

```
A (finish M8/M9 VM research, M2-generation-specific)
   -> exit gate: round trip proven, OR documented SEP/VM-impossibility finding
B (build P3 mutation pipeline against whichever target A validates)
   -> exit gate: spec/build-spec.md's phase-3 acceptance criteria
C (hobbyist SecurityMode-profile reference doc, grounded in B's real evidence, lives in reports/ in this repo)
   -> exit gate: every claim cited; golden-rule review passed
D (governance re-check, including the still-open host-cleanup question)
   -> gates completion of the whole plan
```

Nothing after A can start before A's exit gate is recorded in `progress/milestones.md`, matching this project's own existing discipline for `spec/phased-plan.md`'s phases. If A concludes that a VM can't prove the round trip, B's target shifts to real scratch hardware per `plans/phase-3.md`, and the rest of the sequence is unaffected — C depends on *having* a proven round trip, not on it having come from a VM specifically.

## 4. Explicit non-goals

- No workstream here builds a kext, a custom kernel, or any driver. This plan is documentation and a (gated) mutation-pipeline implementation for *this project's own* existing, specified scope — never a new artifact that itself requires loading in `Reduced`/`Permissive` mode.
- No workstream here creates any link, reference, or dependency between this repository and any other folder or project — no shared code, no cross-repo documentation link, no configuration coupling. Every deliverable in this plan lives entirely inside `the-ant-experiment`.
- No workstream here changes this project's refusal conditions or golden rules. Any future request that would (e.g., "just automate the 1TR credential step for convenience") is refused under `spec/build-spec.md`'s existing terms, not reopened by this plan.
