# Tool Analysis: `bputil-eval` — evaluation brief toward an offensive-informed threat-intelligence defence tool

**Status:** analysis document (no code change proposed yet)
**Author intent:** a self-contained technical + functional briefing that a downstream
*evaluator agent* can read and reason against without re-deriving the architecture from
source. Section 8 defines what that agent should produce.
**Grounding:** every claim below was verified against the code in `src/` and the spec
documents in `spec/` on 2026-11-11. Absent pieces are labelled as such.

---

## 1. What the tool is

`bputil-eval` is a single statically-linked Rust binary (`Cargo.toml`, release profile:
`lto + strip`) that **measures and, in principle, changes an Apple Silicon Mac's
boot-security mode** — exclusively through Apple's own administrative gates
(`bputil`, `kmutil`, `csrutil`), never around them.

The three modes it understands are Apple's own:

| Mode | Meaning |
|---|---|
| `Full` | default; everything Apple-signed |
| `Reduced` | third-party kexts allowed via a SEP-signed AuxKC |
| `Permissive` | a fully custom/unsigned kernel may boot (SSV off) |

Serving model for the "threat-intelligence" read of this: a `SecurityMode` that is not
`Full` — or an unexpected enrolled boot object — is a **high-signal, historically
persistent indicator** on macOS. An attacker with local privileged access who weakens
boot security (disables SSV, enrols an AuxKC or a custom kernel) has planted a
persistence/defence-impairment artifact that survives restarts and reinfections. This
tool's core capability is *measuring exactly that, cryptographically-evidenced and
hard to fake from software alone*.

The tool is explicitly **not** an exploit or bypass tool. Golden rules
(`spec/build-spec.md`): owned devices only; supported mechanisms only; read-only by
default; human owner physically in 1TR for any mutation; one container, always
reversible; no Activation-Lock/MDM/FileVault circumvention; an invariant violation is a
disclosure finding, not a capability; honesty of state (never claim a change without a
fresh measurement).

## 2. Architecture as built

Module map (one audited command wrapper beneath everything):

```
src/main.rs        CLI surface, exit-code mapping, no business logic
src/wrapper.rs     the ONLY place std::process::Command is called; records
                   argv, exit code, stdout, stderr, stdout_sha256 per call
src/env.rs         macOS vs 1TR detection, chip/build; is_mutation_allowed()
src/state/mod.rs   BootState model + validate() validity predicate
src/state/collect.rs  read-only collection: shells Apple tools via wrapper -> BootState
src/state/img4.rs  IMG4/IM4M manifest DER decoding via the `image4` crate (no unsafe,
                   no signature verification — records, never asserts)
src/state/diff.rs  structurally-fielded BootState diff (shared by plan and verify)
src/plan.rs        current state x target profile -> PlannedTransition (data only)
src/report.rs      Report type + hash-chained evidence bundle writer
src/authorize.rs   P3 stub (doc comment only)
src/execute.rs     P3 stub (doc comment only)
src/verify.rs      P3 stub (doc comment only)
```

Enforced-not-just-documented rules:

- **`scripts/ci_guards.sh` fails the build** if any module other than `wrapper.rs`
  references `std::process::Command`, or if any credential-shaped field
  (`password`, `passphrase`, etc.) appears in the code.
- `plans/` golden-file tests (`tests/fixtures/plans/*.json`) freeze the exact
  `bputil`/`kmutil` argv sequences per transition; any silent change to planned
  command sequences breaks the build.

### Data plane

`BootState` (`spec/contract-spec.md` shapes, `state/mod.rs`):

- `schema_version`, `captured_at` (RFC3339, must not be in the future)
- `environment` (`MacOs | OneTrueRecovery`)
- `host` — chip, macOS build, **masked serial (≤ 4 chars)** — deliberate minimisation
- `target_container` — `security_mode`, `ssv_enabled`, `allows_custom_kernel`,
  `allows_third_party_kexts`, `volume_group_uuid`
- `enrolled_objects[]` — role (`Llb|IBoot|KernelCache|AuxKc|CustomBootObject`),
  sha384 (96 lowercase-hex enforced), signer (`Apple|SepLocalPolicy`)
- `other_containers[]` — per-container mode for the `SingleContainerTouched` invariant
- `evidence.raw_outputs[]` — every security-relevant command: argv, exit code,
  stdout sha256

`validate()` rejects inconsistent readings rather than clamping them: `Permissive` with
SSV on, `custom kernel` outside `Permissive`, third-party kexts under `Full`, a
`CustomBootObject` not signed by `SepLocalPolicy`, disjoint-container violations, future
timestamps. **This is the adversary-detection property in miniature:** a mismatch
between claimed state and observed state is an error, not a correction.

### Control plane

`PlannedTransition` (`plan.rs`) is pure data: from/to modes, target volume group, the
exact planned argv with an `authoritative_source` string per command, consequences in
plain language, invariants to check post-apply, and `requires` (environment must be 1TR,
owner credentials required for mutation). The transition graph is conservatively
modelled: `Full -> {Reduced, Permissive}` and both revert to `Full` only — no
`Reduced <-> Permissive` edge. No-op plans (already at target) carry zero commands and
require no credentials.

### Evidence plane

`report.rs` writes `evidence/<session_id>/report.json` plus `report.sha256`
(hash-chained, tamper-evident; real worked example in
`evidence/vm-sec-research-25D125/`, independently verifiable with `shasum -a 256 -c`).
`ValidReport` refuses to write a "passing" report whose invariants failed with
exit 0. Only `evidence.raw_outputs` (the security-relevant reads) are hashed in —
known-unstable outputs (`diskutil info /` free-space counters, uptime-derived `ioreg`
values) were deliberately excluded so "evaluate twice differs only in timestamp" holds,
the literal P1 exit gate.

### Environment gate

`env::detect()` confirms macOS by the presence of Finder.app; otherwise it requires
`bputil -d`'s OS Type to read "one true recoveryOS". Any recovery variant it cannot
positively classify (e.g. fallback recovery) **fails closed** — it is neither `MacOs`
nor `OneTrueRecovery` and therefore mutation-eligible by nothing. `is_mutation_allowed()`
is derived fresh on every call: never cached, never flag-overridable.

## 3. Functional inventory (what actually runs today)

CLI surface (`cargo run -- <cmd>`), all read-only except the stubs:

| Command | Status | Notes |
|---|---|---|
| `evaluate [--json]` | ✅ working | read-only BootState; degrades gracefully without sudo; twice-run diff = timestamp only (P1 gate proven) |
| `plan <full\|reduced-kexts\|permissive-custom-kernel> [--json]` | ✅ working | refuses from `Unknown` mode (exit 11, fail-closed proven live); golden-file tested |
| `verify --baseline <path> [--json]` | ✅ working | structural diff only; **invariant assertion is P3**, `invariants: []` is honest about it; 1 MiB pre-read size cap on untrusted baseline JSON (found by vuln_res audit, test-proven) |
| `report [--out-dir] [--session-id]` | ✅ working | hash-chained bundle |
| `apply` / `revert` | ❌ stubs | print "not implemented (P3/P4)", exit non-zero, on purpose |

Exit codes (spec-defined): `0` ok, `11` parse/refusal; `10` (apply outside 1TR) and
`13` (invariant violation → halt + preserve evidence + disclosure route) are specified
for the unbuilt P3 mutator.

Build health at last recorded run: 43 tests, `clippy -D warnings` clean, `fmt` clean,
both CI textual guards pass (`vuln_res/knowledge/build-test-clippy-fmt-clean-2026-11-10.md`).

**Proof of concept provenance:** an end-to-end chain was executed 2026-11-10 on a
disposable Tart VM the project built — evaluate→Full, apply(1TR, human-typed
authorization)→Reduced, verify, revert→Full, apply→Permissive, verify — producing the
real diff (`security_mode: Reduced → Permissive`, `ssv_enabled: true → false`,
`allows_custom_kernel: false → true`) in `evidence/vm-sec-research-25D125/`. Crucially,
**every mutation was typed live by a human owner**; the mutation pipeline has not been
built into the binary, by rule.

## 4. The companion `vuln_res/` suite (the offensive-informed half)

A second, deliberately scoped adversarial capability rides in the same repo: an agent
suite (`vulnres-recon`, `vulnres-fuzz-harness`, `vulnres-triage`,
`vulnres-exploit-dev`, `vulnres-disclosure`, `vulnres-environment-runner`,
`vulnres-orchestrator` under `.claude/agents/`) that hunts bugs **in this toolchain's own
code and dependency tree** — never in Apple's platform. Its discipline is directly
transplantable intelligence tradecraft:

- **TTP-informed posture** (`vuln_res/plans/07-ttp-informed-research-posture.md`),
  modelled on Project Zero Naptime/Big Sleep, AIxCC-caliber fuzzing, ClusterFuzz triage,
  Pwn2Own-style multi-step chaining — as *technique*, applied only to owned code.
- **Compound knowledge across sweeps:** `sweep-reports/` (one file per finding, indexed,
  plain-language description mandatory on every exploit-grade finding) and `knowledge/`
  (durable facts: fuzz coverage, advisory-DB snapshots, cleared parser patterns,
  environment profiles per `knowledge/environments/SCHEMA.md`).
- **Live returns already:** two real host-independent-parsing findings were found and
  fixed this way (`contains()`-linter technique, `sweep-reports/2026-11-11-001-*`),
  plus the verify baseline size-cap finding from `vuln_res/AUDIT.md` §1.2.
- **Disposition discipline:** every agent executes inside a registered disposable
  environment, per-action user approval; Apple-enforcement gaps are routed to
  coordinated disclosure, never weaponized.
- A `vulnres-pattern-analysis` skill cross-sweeps recurring bug classes and correlates
  them against public research on *the same class* — scope-checked so that generic
  technique knowledge is kept and anything target-specific to Apple's platform is
  discarded.

## 5. Analysis — what is genuinely threat-intelligence-grade already

1. **A trustworthy measurement primitive.** The single hardest problem in endpoint
   intelligence is evidence you can trust. The audited wrapper + hash-chained bundle +
   validity predicate solves the local-fakeability problem for its own measurements:
   every raw read is recorded, hashed, and independently re-verifiable.
2. **A schema for the attacker-relevant state space.** `BootState` *is* a compact IOC
   schema for macOS boot-chain weakening: mode, SSV, kext/custom-kernel allowances,
   enrolled objects with signs and digests, container inventory.
3. **Diff-as-detection.** `state::diff.rs` is already the drift-detection primitive the
   `Fleet Boot-State Drift Watch` proposal builds on — a baseline/fresh-state structured
   delta is exactly continuous-detection logic.
4. **Fail-closed culture as a security property.** Unknown states are errors, unknown
   environments are non-actionable, no-op plans require nothing. An evaluator can trust
   that the tool does not guess.
5. **Proven obverse capability.** The vuln_res pipeline demonstrates that the surrounding
   methodology (recon → fuzz → triage → minimisation → disclosure) genuinely finds and
   fixes vulnerabilities — i.e. the "offensive technique, defensively applied" claim is
   evidenced, not aspirational.

## 6. Analysis — current gaps, technical and functional

Ordered by how much they bound the tool's intelligence capability today:

1. **No temporal layer / baseline store.** `verify` diffs against one ad-hoc JSON file.
   There is no persistent baseline, no scheduling, no alerting surface, no history —
   detection is a manual two-step run, not a capability.
2. **Single-host ceiling.** Nothing fans out; no enrollment list, no SSH runner, no
   fleet view. (`projects/03-fleet-drift-watch/PROPOSAL.md` specifies exactly this,
   unbuilt.)
3. **No CTI interoperability.** No STIX 2.1/TAXII emission, no ATT&CK or ATT&CK-like
   technique tagging on findings, no IOC format consumption/emission. Intel value dies
   at the edge of this repo's markdown.
4. **Coverage gaps inside the measurement itself:**
   - `enrolled_objects` remains empty in practice: the IMG4 parser (`state/img4.rs`) is
     decoder-proven but **not wired into `state::collect`** (blocked on `bputil -d -j`
     / a confirmed manifest path — `plans/phase-1.md` item 1).
   - `other_containers[].security_mode` is hardcoded `Unknown` (deliberate, documented
     in `CLAUDE.md`) — cross-container posture is a placeholder.
   - `security_mode` degrades to `Unknown` without sudo, silently reducing detection
     fidelity; there is no posture-confidence field, so a consumer cannot distinguish
     "measured Full" from "unmeasured".
   - No downgrade/rollback observables (e.g. LocalPolicy/boot-object version deltas)
     anywhere in the schema.
5. **The mutating half is intentionally nonexistent.** `authorize`/`execute`/`verify`
   invariant assertion are P3 stubs. For a *defence* tool this is fine; for
   "prove/demonstrate exploit impact" workflows (AIxCC-style) the missing mutation and
   re-verification loop is the largest absent mechanical piece — and the one the phased
   plan's human-in-1TR gate surrounds most deliberately.
6. **Evidence anti-tamper is hash-only.** `report.sha256` proves internal consistency,
   not authorship. No signature, no key custody, no transparency-log append
   (`projects/products/01-attestation-bundle/` covers the design, unbuilt).
7. **No confidence telemetry.** Environment detection relies on `bputil -d`'s OS Type
   string, acknowledged in `env.rs` as not 100% consistent across builds; nothing
   surfaces detection confidence to consumers.
8. **No intel-feedback loop.** Findings, sweeps, and knowledge accumulate as markdown,
   but nothing synthesizes "what changed about the threat landscape since the last
   sweep" into priorised collection — pattern analysis exists but is per-sweep, not
   continuous.
9. **Hardware generativity.** Test fixtures cover one host's reality; no chip-generation
   matrix (the P5 gate's problem), so generalisation of measurements across M-series
   generations is under-evidenced.

## 7. Threat-intelligence defence mapping (suggested, for the evaluator to critique)

The repo's own "APT-mindset framing" in `projects/*/PROPOSAL.md` already performs the
defensive inversion explicitly. The tool's primitives map onto a classic CTI/detect
pipeline as follows — offered as a starting hypothesis, not settled architecture:

| Pipeline role | Existing primitive |
|---|---|
| Collection | `state::collect` via audited wrapper |
| Normalisation / indicator extraction | `BootState` validity predicate + enums |
| Detection (state-drift) | `state::diff` + planned/fresh delta |
| Evidence / auditability | `report.rs` hash-chained bundle |
| Adversary-strategy awareness | `vuln_res` TTP-informed research posture |
| Response (hard rollback to a known-good posture) | `plan full` + (unbuilt) gated executor |

Natural ATT&CK-style technique coverage for the *indicator set* (for the evaluator to
validate against a current matrix): defence-impairment via SSV/SIP weakening (~Impair
Defenses), kext-based persistence (~Kernel Modules and Extensions), bootkit-class
persistence (~Pre-OS Boot). The tool can *detect the resulting configuration*; it
cannot and must not become an exploitation or bypass instrument — that boundary
(golden rules §2, §6, refusal conditions in root `CLAUDE.md`) is what makes the
intelligence collection defensible and legal, and must survive the pivot untouched.

## 8. What the evaluator agent should produce

Read this document plus `README.md`, root `CLAUDE.md`, `vuln_res/CLAUDE.md`,
`spec/build-spec.md`, `spec/contract-spec.md`, `spec/phased-plan.md`, and
`projects/*/PROPOSAL.md`, then produce:

1. **Capability audit** — confirm/refute each claim in §3/§5 against source and tests,
   noting anything this brief overstates.
2. **Gap ranking** — budget-weighted ordering of §6 items as they gate a
   threat-intelligence-defence productisation, with the cheapest "unlocks the most"
   item first. (Prior hypothesis: a fleet/baseline/scheduling layer — the drift-watch
   proposal — converts existing, proven read-only measurement into a real detection
   capability with zero new hardware risk.)
3. **Interoperability recommendation** — whether intel emission should be STIX 2.1
   first, or an internal delta/attestation format first; and where ATT&CK-style tagging
   belongs (finding templates vs BootState itself).
4. **Guardrail stress-test** — for each proposed enhancement, state whether it is
   achievable **without** loosening any golden rule, CI guard, or the
   no-mutation-without-1TR gate; flag any proposal that requires loosening them.
5. **Decision request** — a crisp "build next / research next / don't build" list,
   resolvable by the owner without code changes.

## 9. Constraints that must survive the pivot (non-negotiable)

- Read-only by default; mutation only via Apple's own tools, only in confirmed 1TR,
  only with a present human owner typing credentials. No credential handling anywhere.
- No bypass of, or fault-injection into, Boot ROM/SEP/iBoot/signature paths — not on
  real devices, not in VMs, not on extracted firmware.
- Findings resembling Apple-enforcement gaps are disclosure items, never capabilities.
- Execution happens in registered disposable environments, per-action approved; the
  session host stays unmodified.
- Evidence honesty: fresh measurement or it isn't a claim.
