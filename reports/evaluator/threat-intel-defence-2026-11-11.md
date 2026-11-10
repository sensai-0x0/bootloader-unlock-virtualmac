---
title: "Deliverable 3 — CTI mapping critique + guardrail stress-test (§5, §7, §8.4)"
child_plan: plans/threat-intel-defence.md
parent: plans/tool-analysis-parent.md
date: 2026-11-11
inputs:
  - reports/evaluator/high-offensive-2026-11-11.md (capability audit)
  - reports/evaluator/gaps-roadmap-2026-11-11.md (ranked items 1–7 + flags)
attandck_matrix_version: "v20 (released Oct 2026, per attack.mitre.org banner during validation)"
---

# Threat-intel-defence — critique and stress-test

## C1 — critique of the §5 strengths and §7 pipeline mapping

| §5 strength | Audit verdict | Survives? |
|---|---|---|
| Trustworthy measurement primitive | wrapper + hash-chained bundle + validity predicate all live and test-backed (`high-offensive` A2) | **Survives qualified**: proven for *internal consistency*; hash-only anti-tamper means it is not yet proof of authorship (gap 6) — "cryptographically-evidenced and hard to fake from software alone" holds against software forgery, not against an attacker who controls the reporting host's own reporting |
| IOC schema for boot-chain weakening | `BootState` fields confirmed against `spec/contract-spec.md` + `state/mod.rs` | **Survives with coverage caveat**: `enrolled_objects` is always empty in practice (IMG4 unwired), `other_containers`/posture-confidence/unmeasured degradation blur the schema's own honesty — the schema is sound, its sampling is incomplete |
| Diff-as-detection | `state/diff.rs` live, shared by plan/verify | **Survives as primitive; not yet a capability** — nothing schedules it or stores a baseline (gap 1); it is a component, not continuous detection |
| Fail-closed culture as a security property | `validate()` rejects-not-clamps with named tests; `env` fails closed on unclassifiable recovery; `plan` exits 11 from `Unknown` | **Survives unqualified** — the tool demonstrably does not guess |
| Proven obverse capability | two fixed findings + size-cap finding, all test-backed | **Survives unqualified** |

## §7 CTI pipeline mapping — re-rendered

| Pipeline role | Source's primitive | Verdict | Basis |
|---|---|---|---|
| Collection | `state::collect` via audited wrapper | **live** | audit A1.2/A2: reads only via wrapper; Apple tools only |
| Normalisation / indicator extraction | `BootState` + validity predicate | **live (partial fidelity)** | schema sound; confidence fields missing; `Unknown` degradation |
| Detection (state-drift) | `state::diff` | **partial** | primitive confirmed; no baseline store/scheduling/alerting |
| Evidence / auditability | `report.rs` hash-chained bundle | **live (hash-only)** | audited A2.7; third-party verifiability is precisely what's missing |
| Adversary-strategy awareness | `vuln_res` TTP-informed posture | **live (process-anchored)** | roster + scope contract + fixed findings; enforcement is by process docs, not code |
| Response (hard rollback) | `plan full` + ungated executor | **hypothesis** | P3/P4 stubs; human-with-physical-access phases |

## ATT&CK technique validation (against v20)

| Suggested mapping | Status | Notes |
|---|---|---|
| SSV/SIP/SSV-off weakening ~ **T1562 Impair Defenses** | **VALID** (parent active) | Note v20 sub-tech **T1562.010 Impair Defenses: Downgrade Attack** — a *more precise* fit for boot-mode weakening than the parent, and it maps directly onto ranked item 3 (downgrade/rollback observables). Recommend tagging the drift finding T1562.010 when observables land; the v20-introduced sibling **T1685 (Disable or Modify Tools)** should be re-checked for absorption of macOS Impair-Defenses semantics before shipping tags. |
| Kext-based persistence ~ **T1547.006 Kernel Modules and Extensions** | **VALID** | macOS kext explicitly in scope; requires `allows_third_party_kexts` + AuxKC/enrolled-object coverage — hence attention to gap 4a (`enrolled_objects` currently empty) |
| Bootkit-class persistence ~ **T1542 Pre-OS Boot** | **VALID** | sub-tech T1542.003 Bootkit is the precise match for custom-kernel/SSV-off; same caveat: meaningful tagging needs `enrolled_objects` + `allows_custom_kernel` fidelity |

**Coverage gap confirmed:** the current indicator set *detects the configuration* but
cannot yet *tag* these techniques with full fidelity — unmeasured-`Unknown` states and
empty `enrolled_objects` mean a detected state can under-determine its technique. This
is exactly why the gaps roadmap puts posture-confidence (rank 1) and IMG4 wiring
(rank 5 research) ahead of any STIX emission (rank 7).

## C2 — guardrail stress-test (source §8.4)

Rules tested per item: golden rules 1–8 (`spec/build-spec.md:12-19`), both CI guards
(`scripts/ci_guards.sh`, verified passing live), no-mutation-without-1TR gate, §9
constraints (`tool-analysis-parent.md`).

| Ranked item | Passes without loosening? | Binding guardrail | Compliant variant / condition |
|---|---|---|---|
| 1 posture-confidence + cross-container fields | **YES** | golden rule 8 (honesty of state) | confidence must be derived fresh per measurement, never a persisted flag; the field must make *unmeasured* louder, not quieter |
| 2 baseline store + single-host alerting | **YES, with condition** | §9 evidence-honesty | alerts only from a fresh `evaluate`; baseline updates only via explicit acknowledge-as-expected — never silent (drift-watch proposal rule, pre-scheduling) |
| 3 downgrade/rollback observables | **YES** | P1 twice-run gate | `schema_version` bump + re-run the twice-run-equals-timestamp-only goldens; read-only additions |
| 4 fleet fan-out (SSH) | **YES — but highest operational risk** | golden rules 1, 3, 6; §9 per-action approval | keep by-construction no-mutation (no `apply`/`revert` in the runner, per the proposal); enrollment strictly by hand, per-fleet opt-in re-asked on growth; explicitly surface the runner-SSH-key compromise risk to the owner before first enrollment; **no auto-discovery/scanning, ever** |
| 5 IMG4 wiring (post-research build) | **YES** | golden rule 2; §9 "no undocumented poke" spirit | follow `plans/phase-1.md`'s own protocol: try `bputil -d -j` first; no filesystem-path guessing at local-policy storage without an architecture doc or explicit sign-off |
| 6 attestation bundle | **YES** | `NoCredentialHandling` | decide key custody as a *new explicit decision* with the owner (long-lived signing key is itself an asset to protect); design proposal already scopes it |
| 7 internal delta emission + STIX projection | **YES, with scrubbing condition** | masked-serial minimisation (`host.serial_masked`) | emission must inherit the schema's minimisation; add an explicit "nothing identifying beyond `serial_masked` leaves the bundle" check that keeps hash-only proof intact |
| 8 full confidence telemetry | **YES** | none sharp | data dependence on fleet layer is the real limiter, not a guardrail |
| 9 intel-feedback loop | **YES** | §9 execution scope | markdown/synthesis only; no new execution privileges |
| 10 hardware matrix / IPSW simulation | **YES** | §9 disposable-environment rule | run inside the registered disposable environment only (`plans/research-environment.md`); never on production hosts |
| 11 mutation half (P3/P4) | **YES — only as the human-in-1TR phases already define it** | golden rule 4; the entire gate | **"Don't build as proposed" for anything that automates, scripts, or represents-away the human-typed owner credential step** — including AIxCC-style impact loops: they may be *designed* around the human gate (the phases already do), never around it |

**No proposal in the ranked list requires loosening any golden rule, CI guard, or the
1TR gate.** Two items carry conditions that are cargar material rather than
show-stoppers (baseline acknowledge-flow before scheduling; STIX scrubbing policy).

**Handoff:** every item above with a green pass enters `evaluator-decisions.md`'s D2
buckets; the two conditional items enter with their conditions attached to the entry.
