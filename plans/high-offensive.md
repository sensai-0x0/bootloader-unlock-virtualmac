---
title: Theme A — the offensive-informed half (tool identity + vuln_res tradecraft)
source_document: archive/tool-analysis-offensive-threat-intel-defence.md (§1–§4)
parent: tool-analysis-parent.md
role: agent (evaluator agent)
status: pending
deliverable: reports/evaluator/high-offensive-<YYYY-MM-DD>.md
---

# High-offensive — verify what actually exists before anything is ranked

**Why this file runs first:** every downstream gap ranking and decision rests on the
claim inventory in source §1–§4. If a claim is overstated, the ranking built on it is
wrong. Your job here is the §8.1 **capability audit**: confirm or refute each claim
against source and tests, and note anything the brief overstates. No ranking yet —
that is `gaps-roadmap.md`'s job.

---

## Parent task A1 — confirm the tool's identity and boundaries (source §1)

Child tasks:

- [ ] **A1.1** Confirm the binary description: statically-linked Rust, release profile
      `lto + strip`. Check `Cargo.toml` directly.
- [ ] **A1.2** Confirm the tool reaches boot-security state **only through** `bputil`,
      `kmutil`, `csrutil` — grep `src/` for any invocation path other than
      `src/wrapper.rs`.
- [ ] **A1.3** Confirm the three security modes (`Full`, `Reduced`, `Permissive`) and
      their meanings match Apple's actual semantics (`bputil -h` output on an owned
      test host, or `spec/contract-spec.md` if no host is available).
- [ ] **A1.4** Confirm the golden rules list quoted in §1 is exactly what
      `spec/build-spec.md` states — quote both side by side in the deliverable. Flag
      any rule in the brief that is not in the spec (overstatement) or any spec rule
      the brief omits.

**Exit criterion:** a table of claim → confirmed / refuted / overstatement, each row
citing a file and line.

## Parent task A2 — audit the architecture claims (source §2)

Child tasks:

- [ ] **A2.1** Verify every module in the §2 module map exists with the claimed
      responsibility. Flag modules that do more or less than stated.
- [ ] **A2.2** Enforced rules, not just documented: run
      `scripts/ci_guards.sh` (or read it) and confirm it fails the build if
      (a) any module other than `wrapper.rs` references `std::process::Command`,
      (b) any credential-shaped field appears in code. Record how each guard is
      actually implemented.
- [ ] **A2.3** Golden files: confirm `tests/fixtures/plans/*.json` freeze exact
      `bputil`/`kmutil` argv per transition and confirm the test would break on a
      silent change. Read one fixture end to end.
- [ ] **A2.4** Data plane: verify each `BootState` field listed in §2 against
      `src/state/mod.rs` and `spec/contract-spec.md`, including masked serial
      (≤ 4 chars) and sha384 hex enforcement.
- [ ] **A2.5** Validity predicate: confirm `validate()` rejects (not clamps) each
      inconsistency listed in §2 (Permissive+SSV-on, custom kernel outside Permissive,
      third-party kexts under Full, `CustomBootObject` not `SepLocalPolicy`-signed,
      disjoint-container violations, future timestamps). Name the test proving each.
- [ ] **A2.6** Control plane: confirm `PlannedTransition` is pure data, the transition
      graph has no `Reduced <-> Permissive` edge, and no-op plans carry zero commands
      and require no credentials.
- [ ] **A2.7** Evidence plane: run `shasum -a 256 -c` against
      `evidence/vm-sec-research-25D125/report.sha256` and confirm it validates (or
      document that it cannot from this checkout, and why). Confirm `ValidReport`
      refuses a "passing" report whose invariants failed with exit 0, and the
      exclusion list for unstable outputs.

**Exit criterion:** per-claim verdicts with file/line or test citations.

## Parent task A3 — audit the functional inventory (source §3)

Child tasks:

- [ ] **A3.1** For each CLI command in the §3 table, confirm status and behaviour:
      `evaluate` (twice-run diff = timestamp only), `plan` (exit 11 from `Unknown`
      mode), `verify` (structural diff only, `invariants: []`, 1 MiB baseline
      pre-read size cap — find the test), `report`, `apply`/`revert` stubs.
- [ ] **A3.2** Confirm the exit-code contract (`0` ok, `11` parse/refusal, `10` and
      `13` specified but unused) in `spec/contract-spec.md` and `src/main.rs`.
- [ ] **A3.3** Re-derive build health: run `cargo test`, `cargo clippy -D warnings`,
      `cargo fmt --check` and compare against the recorded result
      (`vuln_res/knowledge/build-test-clippy-fmt-clean-2026-11-10.md`: 43 tests).
      Report any drift.
- [ ] **A3.4** PoC provenance: read `evidence/vm-sec-research-25D125/` and confirm
      the recorded Reduced → Permissive diff (`security_mode`, `ssv_enabled: true →
      false`, `allows_custom_kernel`: false → true) and that the doc's claim
      "every mutation was typed live by a human owner" is consistent with what the
      evidence bundle can and cannot show (state what the evidence proves and what
      it merely records).

**Exit criterion:** functional inventory table reproduced with a verdict per row.

## Parent task A4 — audit the vuln_res suite claims (source §4)

Child tasks:

- [ ] **A4.1** Confirm the agent roster exists under `.claude/agents/` with the
      seven names listed and read one of them to confirm scope ("this toolchain's own
      code and dependency tree — never Apple's platform") is enforced, not just stated.
- [ ] **A4.2** Confirm the two live findings: the `contains()`-linter technique /
      `sweep-reports/2026-11-11-001-*` files, and the verify baseline size-cap finding
      (`vuln_res/AUDIT.md` §1.2). For each, confirm it was **found and fixed**
      (the fix commit or test).
- [ ] **A4.3** Confirm compound-knowledge structure: `sweep-reports/` indexed with
      plain-language descriptions mandatory on exploit-grade findings; `knowledge/`
      durable facts including `knowledge/environments/SCHEMA.md`.
- [ ] **A4.4** Confirm disposition discipline (disposable environments, per-action
      approval, Apple gaps routed to disclosure) is stated where the source claims
      it, and identify whether it is enforced by process or by code.

**Exit criterion:** tradecraft claims table with verdicts and citations.

---

## Deliverable

Write `reports/evaluator/high-offensive-<YYYY-MM-DD>.md` containing:

1. The four per-parent verdict tables (A1–A4), each row showing
   *claim → verdict → citation*.
2. A section **"Overstatements found"** — anything the source brief claims beyond
   what source/tests support, however small.
3. A section **"Unverifiable from this checkout"** — claims that need a device (1TR,
   hardware) and how they'd be verified.

Constraints: read-only analysis only; no code changes; the §9 guardrails in
`tool-analysis-parent.md` bind everything you do.

**Handoff:** your verdict tables are the ground truth that `gaps-roadmap.md`
consumes. Do not editorialise about priorities here.
