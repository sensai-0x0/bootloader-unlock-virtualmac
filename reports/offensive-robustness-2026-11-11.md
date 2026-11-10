---
title: Offensive-lens robustness analysis — bputil-eval
date: 2026-11-11
method: orchestrator + 4 short-lived workers (1 source audit, 3 web research), orchestrator re-verified critical claims against source
builds_on: reports/evaluator/*-2026-11-11.md (does not repeat them)
status: analysis only — no code changed
---

# Offensive-lens robustness analysis — `bputil-eval`

## 0. Bottom line

The earlier evaluator pack treated the problem as a **fidelity and coverage** problem:
empty `enrolled_objects`, no baseline store, no CTI emission. Viewed by an attacker,
the bigger problem is **trust**. The tool measures boot posture from inside the OS it is
judging, and today the measurement can be forged by:

- a **non-root** user, by putting a fake `bputil` or `sudo` earlier in `PATH` (verified:
  `Command::new(bare_name)` at `src/wrapper.rs:45`; this host has ~12 user-writable
  directories ahead of `/usr/bin`). The fake output is recorded as
  `posture_confidence: Measured`, `security_mode: Full`.
- **anyone** who can write to `evidence/`, who can edit `report.json` and recompute the
  plain sha256 (`src/report.rs:66-77`), or simply replay an old bundle.
- **anyone** who supplies a `--baseline`, because it is deserialised but never passed
  through `validate()` (`src/main.rs:200`) and the diff ignores host identity and OS
  build.

Even with all of that fixed, three publicly documented SIP bypasses leave
`csrutil status` reading *enabled*:

- Shrootless, CVE-2021-30892
- Migraine, CVE-2023-32369
- the `storagekitd` bypass, CVE-2024-44243

A status-flag reader cannot see the result of any of them. For the tool to be
threat-intel grade it needs three things:

1. a **hardened collection path**
2. **cross-checked, content-level observables**
3. an **external root of trust**, which on Apple Silicon means Apple's Managed Device
   Attestation

Only (3) defeats a root attacker. (1) and (2) raise the cost and turn lies into
contradictions.

**Housekeeping, found during this pass:**

- The uncommitted `posture_confidence` wiring in `src/state/collect.rs` breaks
  `state::tests::unknown_mode_in_macos_is_allowed` (`src/state/mod.rs:372`): 61 of 62
  tests pass. The new rule `MeasuredPostureWithUnknownMode` rejects the old fixture.
- The test counts in `CLAUDE.md` (43) and the evaluator reports (55) are stale.

---

## 1. Features and postures (as built)

| Surface | Posture | Honest assessment |
|---|---|---|
| `evaluate` | read-only, fail-closed on unparseable mode | It fails closed on *garbage*. It fails **open on well-formed lies** (F1). |
| `plan` | pure data, refuses `Unknown` (exit 11) | Sound. Trusts `evaluate`'s input completely. |
| `verify --baseline` | 1 MiB cap, structural diff, always exits 0 | Weak detector. No validation, no host binding, no non-zero exit on drift. |
| `report` | sha256 of `report.json` | Catches corruption, not tampering. The raw outputs behind the hashes are discarded, so the evidence cannot be re-audited. |
| `apply`/`revert` | stubs, by rule | Correct. Out of scope. |
| `env::detect` | Finder.app present ⇒ macOS; else `bputil -d` "OS Type" | Fine for read-only use. It becomes safety-critical at P3, where the same PATH-shim issue applies. |
| CI guards | grep for `std::process` outside wrapper; credential-shaped fields | Good. **Missing a third guard: absolute-path allowlist for argv0.** |

## 2. Data flow, with trust boundaries

```
           ┌──────────── TRUST BOUNDARY A: process environment (PATH, LANG, DYLD_*) ─────────┐
CLI ──> env::detect ──> wrapper::run(bare name) ──> Command::new → PATH lookup, full env,     │
                                                    no timeout, unbounded stdout, lossy UTF-8 │
           └─────────────────────────────────────────────────────────────────────────────────┘
                 │ stdout (text, English-keyed)
                 ▼
           ┌──── TRUST BOUNDARY B: Apple-tool text format (drifts across builds, locale) ────┐
           collect: line-substring parsers → SecurityMode / ssv / serial / volume group     │
           kext + custom-kernel flags DERIVED from mode, not measured (collect.rs:152-156)  │
           └─────────────────────────────────────────────────────────────────────────────────┘
                 ▼
           validate()  ── no Full ∧ ¬SSV rule (cheap cross-tool contradiction check missing)
                 ▼
     ┌─── diff (ignores host.*, macos_build, volume_group_uuid, posture_confidence)
     │           ▲
     │     TRUST BOUNDARY C: --baseline JSON  (deserialised, NOT validated, schema not checked)
     ▼
   report → evidence/<session_id>/report.json + sha256   (session_id unsanitised → path traversal)
           TRUST BOUNDARY D: evidence at rest  (unkeyed, unchained, no nonce, no off-host anchor)
```

Missing entirely: **TRUST BOUNDARY E: external attestation.** Nothing in the flow is
anchored outside the measured OS.

## 3. Threat model results

| Adversary | Goal | Today | After fixes in §4 |
|---|---|---|---|
| Non-root local user | make tool report Full | **Succeeds silently** (PATH shim) | Blocked (absolute paths + env_clear) |
| Root, SIP on | same | Succeeds (edit bundle / replay) | Detectable: off-host anchor, nonce, attestation mismatch |
| Root, SIP off (already weakened boot) | same | Succeeds (can shim `/usr/bin`) | **Only attestation and 1TR measurement catch it.** Output must say so. |
| Post-SIP-bypass malware (CVE-2024-44243 class) | persist under "SIP enabled" | Invisible | Partially visible via SSV seal, AuxKC/loaded-kext delta, `csr-active-config` bits |
| Format drift (new macOS, non-English locale) | — | Fails closed, but `evaluate` unusable; SSV parse can latch onto the wrong line | `LC_ALL=C`, `-j` JSON first, per-build fixtures |
| Malicious baseline | false "no drift" / cross-host compare | Accepted | Rejected (validate, schema check, host binding) |

## 4. Missing pieces, ranked (cheapest that unlocks the most comes first)

All items are read-only. None loosens a golden rule, CI guard, or the 1TR gate (§6).

### Tier 0: fix before anything else (hours, code-local)

> **Status (2026-11-11):** items 1–7 implemented on branch `fix/tier0-trust-hardening`
> (81 tests, clippy, fmt, 3 CI guards green; guard 3 negative-tested against planted
> violations). `verify` drift uses exit 1 and inconclusive uses 2, deliberately not 13.
> F4/F6/F7 (csrutil exit code, char-safe serial, anchored SSV line) landed alongside.
> Item 8 belongs to the uncommitted `posture_confidence` wiring on
> `feat/posture-confidence-collect-wiring`, not `main`: its `Ok(non-zero)` arm still
> labels "sudo refused (no cached credential)" as an unparsed root read.

1. **Absolute-path allowlist in `wrapper::run`.** Allowed binaries:
   - `/usr/bin/bputil`
   - `/usr/bin/csrutil`
   - `/usr/bin/sudo`
   - `/usr/sbin/diskutil`
   - `/usr/sbin/system_profiler`
   - `/usr/sbin/sysctl`
   - `/usr/bin/sw_vers`

   Refuse anything else, and add a `ci_guards.sh` rule. (F1)
2. **`env_clear()` + fixed `PATH` + `LC_ALL=C`**, with the environment used recorded in
   the evidence. (F2)
3. **Timeout + stdout cap** in the wrapper. (F3)
4. **Validate the baseline:** `validate()`, `deny_unknown_fields`, a `schema_version`
   check, and refusal on serial/volume-group mismatch. (F12–F14)
5. **Make `verify` exit non-zero** on drift, or when fresh confidence is below
   `Measured`. (F15)
6. **Sanitise `--session-id`** and write with `create_new`. (F11)
7. **Add the cross-tool contradiction rule `Full ∧ ¬ssv_enabled ⇒ error`.** A forger now
   has to fake `bputil` and `csrutil` consistently. (F5)
8. **Fix the red test and correct the sudo-outcome labels.** `sudo -n` returning exit 1
   with "password is required" means *unavailable*, not *unparsed*. (F17, F18)

### Tier 1: make the evidence an artifact a third party can verify (days)

9. **Keep the raw stdout bytes** in the bundle, one file per command, next to the
   hashes. Record each tool's identity: path plus the `codesign` cdhash. (F9)
10. **Hash-chain across runs.** Each bundle commits to the previous head.
11. **Wrap each bundle in DSSE + an in-toto Statement** (subject = bundle digest,
    predicate type e.g. `…/boot-posture/v1`). Add an **RFC 3161 timestamp**.
12. **Ship the head hash off-host immediately** (SIEM / append-only log).

    Optional extra: a Secure Enclave signing key. Document plainly that root can use the
    SEP as a signing oracle, so a signature proves *which device*, not *truth*.
13. **Narrow the meaning of `posture_confidence: Measured`.** It should mean "read via
    pinned binaries with a clean environment". Add `Attested` above it and
    `MeasuredFrom1TR` alongside it. Never let a macOS-side read claim more than
    "consistent claim".

### Tier 2: close the observable gaps a real attacker leaves behind (days–weeks, research-gated)

14. **Parse `bputil -e -j` first, with text as a fallback.** Record which source was used.
    Pull the fields already printed but ignored:
    - Kernel CTRR Status
    - Boot Args Filtering
    - User/DEP-allowed MDM Control
    - Pairing Integrity
    - Signature Type
    - Cryptex1 hash/generation

    Then add LocalPolicy consistency rules:
    - Permissive ⇒ smb0+smb1
    - Reduced+kexts ⇒ smb2 + auxp/auxr
    - CTRR off or boot-args unfiltered ⇒ Permissive

    The `-j` schema is undocumented: capture fixtures on an owned VM first.
15. **Policy vs reality cross-checks.** These need no extra privilege:
    - `kmutil showloaded` aux collection vs `allows_third_party_kexts`
    - `sysctl kern.bootargs` vs boot-args filtering
    - full `csr-active-config` bits vs "enabled"
    - `systemextensionsctl list`
    - `spctl --status`

    These are what move detection past status flags, and the reason the CVE-2024-44243
    class becomes visible.
16. **Downgrade observables.** Monotonic checks on `macos_build`, OS/iBoot/sepOS/LLB
    versions and the Cryptex1 generation across stored runs (ATT&CK T1689 Downgrade
    Attack). Also diff the `lpnh` nonce-hash across runs: a policy change with no `lpnh`
    change, or an `lpnh` change with no recorded event, is a signal.
17. **Stop deriving flags from mode** (F16), or label them `derived` in the output.

### Tier 3: external root of trust (the only defence against root)

18. **Ingest Managed Device Attestation** as an offline, verify-only input. Steps:
    - Accept the MDM- or ACME-delivered certificate chain.
    - Verify it against Apple's Enterprise Attestation root.
    - Check a freshness nonce the operator issued.
    - Read the OIDs:

    | OID | Meaning |
    |---|---|
    | `1.2.840.113635.100.8.13.1` | SIP |
    | `.13.2` | secure boot configuration |
    | `.13.3` | third-party kexts |
    | `.10.1`–`.10.3` | OS/iBoot, sepOS, LLB versions |

    Requirements and limits:
    - macOS 14+, Apple Silicon.
    - Apple *omits* an OID it cannot vouch for: treat a missing OID as `Unknown`, never
      as `Full`.
    - A fresh attestation is rate-limited to once per 7 days.
    - It does not cover SSV, CTRR, boot-args, AuxKC contents or a custom kernel. Those
      stay local-only.

    Then **cross-check attestation against the local read**. A contradiction is a
    high-confidence tamper finding. It also needs no credential handling by this tool,
    because MDM does the requesting.
19. **1TR-side measurement.** Run `evaluate` from paired recoveryOS (the binary needs no
    sudo there) to get a reading outside the possibly-compromised macOS. It stays
    read-only and human-present, consistent with the existing 1TR discipline.

### Tier 4: intel plumbing (after Tiers 0–1, consistent with the prior "internal-first" decision)

20. Use **NDJSON as the default output**, with an **OCSF Compliance Finding** projection
    for SIEMs. Promote to **Detection Finding** only on a threat-threshold drift. STIX
    2.1 stays a later export for sharing (agrees with evaluator D1).
21. **Tag ATT&CK techniques via a versioned lookup table carrying `attack_version`.**
    The matrix is now **v20.1**: Defense Impairment is a new tactic (TA0112), and "Disable
    or Modify Tools" is now T1685. Do not hard-code T1562.001. A clean result must read
    "no indicators observed", never "no rootkit".

| Technique (v20.1) | Covered now | Added by tier |
|---|---|---|
| T1547.006 Kernel Modules & Extensions | mode-derived only | 15, 17 |
| T1542(.002) Pre-OS Boot / component firmware | proxy via mode | 14, 16, 18 |
| T1685 Disable/Modify Tools (SIP/SSV) — *mapping unconfirmed* | status flags | 7, 15 |
| T1014 Rootkit | none (preconditions only) | 14, 15 |
| T1689 Downgrade Attack | none | 16, 18 |
| T1553 Subvert Trust Controls | none | 15 (`spctl`) |

### Tier 5: generalisation

22. **Golden fixtures per macOS 13–26 build**, plus a canary on each beta.

    No authoritative output changelog exists, and a sibling tool (`system_profiler -json`)
    already broke its output on 26.3.1/26.4. Parse leniently around JSON, strictly around
    fields. This overlaps P5's hardware matrix.

## 5. Agent-swarm model for the `vuln_res` suite (Anthropic guidance applied)

Sources:
- <https://www.anthropic.com/engineering/building-effective-agents>
- <https://www.anthropic.com/engineering/multi-agent-research-system>
- <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>
- <https://code.claude.com/docs/en/sub-agents>

Design rules taken from this guidance:

- **Orchestrator + short-lived workers, sized to the task.** Use 1 worker for a lookup
  and 2–4 for a comparison. Multi-agent costs roughly 15× chat tokens, so use it only for
  breadth-first, independent work (independent fuzz targets, parallel research tracks).
  Run dependent stages sequentially: recon → harness → run → triage → disclosure.
- **Every brief has four parts:** objective, output format, allowed tools/sources, and
  explicit boundaries. Vague briefs were the main documented cause of duplicated work.
- **Workers write artifacts to files and return only summaries plus paths.** The
  knowledge store (`vuln_res/knowledge/`, `sweep-reports/`) is the shared memory. The
  orchestrator reads git log and progress notes at session start.
- **Gates between stages are deterministic, not LLM judgment:**
  - sanitizer reproduction
  - exit code and hash checks
  - schema validation
  - independent re-reproduction in a second disposable environment (the
    Mozilla/Firefox pattern: 22 bugs found, each independently VM-validated)
- **The verifier is never the producer.** Producers declare success without end-to-end
  testing, so the orchestrator re-verifies critical claims. This pass did exactly that
  for F1, F10, F12 and the failing test.
- **Scoped tool allowlists per worker**, enforced in frontmatter (`tools` /
  `disallowedTools`):
  - recon: read-only
  - fuzz: sandbox-only
  - disclosure: never executes code
- **Sandboxes have no network by default.** The orchestrator prompt caps worker count and
  tool calls.
- **A human signs off** before any exploit-grade artifact or any disclosure.

## 6. Guardrail stress-test

Every Tier 0–5 item is achievable **without loosening any golden rule, CI guard, or the
1TR gate**:

- **No new mutation path.** Nothing writes to device boot state.
- **No credential handling.** MDA is requested by MDM, not by this tool. 1TR reads need
  no sudo.
- **No bypass research.** CVEs are used only for their *observable aftermath*.
- **New collection commands go through the wrapper**, now with absolute paths.

| Item | Condition attached |
|---|---|
| Tier 1 SEP signing | Must be documented as provenance, not truth. |
| Tier 2 `-j` fixture capture | Must happen on an owned disposable VM, approved per action (host rule in `CLAUDE.md`). |
| Off-host anchoring (12) | Only to an operator-chosen sink. Never send host data to a public transparency log (a public Rekor entry leaks host metadata). |

**Don't build:**
- anything that tries to make a macOS-side read *prove* integrity against root (it can't)
- any automated 1TR entry
- any use of SIP-bypass CVEs beyond their observable state

## 7. Decision request for the owner

- **Build now:** Tier 0 (items 1–8). Small, testable, and it closes the only *silent* trust
  failures.
- **Build next:** Tier 1 (9–13), then item 14's fixture capture → 15 → 16.
- **Research next:**
  - MDA ingestion (18): MDM availability, and whether ADE is required on Mac (not
    confirmed in sources).
  - `bputil -e -j` schema (14).
  - Whether `-d -v <uuid>` works for per-volume reads (it would replace hardcoded
    `Unknown` for `other_containers`).
  - 1TR-side evaluate (19).
- **Don't build:** STIX-first, public transparency-log anchoring of host data, any attempt
  to infer kernel integrity from userland beyond "no indicators observed".

## Appendix: worker provenance and unverified items

- **Source audit:** findings F1–F18. F1, F10, F12 and F17 were re-verified by the
  orchestrator.
- **Apple research.** Source pages:
  - MDA OIDs: <https://support.apple.com/guide/security/sec8a37b4cb2>
  - attestation process: <https://support.apple.com/guide/security/attestation-process-security-sec97eb9e2f2/web>
  - validation guide: <https://developer.apple.com/documentation/devicemanagement/validating-a-managed-device-attestation-attestation.md>
  - LocalPolicy fields: <https://support.apple.com/guide/security/secc745a0845/web>
  - `bputil` man page: <https://keith.github.io/xcode-man-pages/bputil.1.html>
  - `bputil` output fields: <https://eclecticlight.co/2024/04/01/checking-bootable-systems-using-bputil-on-apple-silicon/>
  - `system_profiler` JSON drift: <https://developer.apple.com/forums/thread/820473>
- **ATT&CK/CTI research.** Source pages:
  - macOS matrix: <https://attack.mitre.org/matrices/enterprise/macos/>
  - T1547.006: <https://attack.mitre.org/techniques/T1547/006/>
  - OCSF Compliance Finding: <https://docs.tenzir.com/reference/ocsf/1-3-0/classes/compliance_finding>
  - CVE-2024-44243 analysis: <https://thehackernews.com/2025/01/microsoft-uncovers-macos-vulnerability.html>
- **Unverified, confirm before relying on:**
  - the T1562.001 → T1685 successor mapping for SIP-disable
  - the exact D3FEND IDs beyond D3-BA
  - the `kmutil showloaded --collection aux`, `systemextensionsctl` and `spctl` command
    forms on current macOS
  - the Fleet/Jamf/Kandji check details
  - the ADE requirement for MDA on Mac
  - Anthropic July-2026 sandbox-escape reporting (secondary press only)
