---
title: "Deliverable 1 — Capability audit of the archived brief (§1–§4)"
child_plan: plans/high-offensive.md
parent: plans/tool-analysis-parent.md
date: 2026-11-11
audit_commit: d9d2c8b (pack setup on main)
verdict_legend: CONFIRMED / CONFIRMED WITH CAVEAT / OVERSTATED / CITED-ONLY
source_document: plans/archive/tool-analysis-offensive-threat-intel-defence.md
---

# Capability audit — high-offensive (source §1–§4)

Executed per `plans/high-offensive.md` on this checkout, 2026-11-11. Every row cites a
file+line or a named test. Live re-derivations performed: `cargo test` (55 passed),
`cargo clippy -- -D warnings` (clean), `cargo fmt --check` (clean),
`./scripts/ci_guards.sh` (both guards OK), `shasum -a 256 -c verify_permissive.sha256`
(OK).

## A1 — tool identity and boundaries (source §1)

| Claim | Verdict | Citation |
|---|---|---|
| Release profile `lto + strip` | CONFIRMED | `Cargo.toml:26-28` (`lto = true`, `strip = true`) |
| "Statically-linked Rust binary" | CONFIRMED WITH CAVEAT | wording inherited from the spec's deliverable (`spec/build-spec.md:22` "A single statically linked Rust binary"); `Cargo.toml` itself proves `lto+strip` but not full static linkage (no `crt-static`); not independently verifiable from build config alone |
| Reaches boot-security state exclusively through `bputil`/`kmutil`/`csrutil` | CONFIRMED | invocation sites: `src/state/collect.rs:73,81,85,92` (`diskutil`/`csrutil`/`bputil`), `src/env.rs:56` (`bputil`), `src/plan.rs:149,159,171,183,251,263,291` (`bputil`/`kmutil`/`csrutil`) — all Apple tools; note `diskutil`/`ioreg` are read-only Apple *observation* tools, a minor nuance on "administrative gates" wording but no violation of golden rule 2 |
| Three modes `Full`/`Reduced`/`Permissive` with stated meanings | CONFIRMED | `SecurityMode` enum `src/state/mod.rs:18-24`; mode meanings encoded in `validate()` rules (`:155-163`) and `plan.rs` consequences (`:179`) |
| Golden rules paraphrase matches spec | CONFIRMED | `spec/build-spec.md:12-19` lists exactly eight rules; the brief's paraphrase (owned devices; supported mechanisms; read-only default; human owner in 1TR; one container reversible; no circumvention; invariant = disclosure finding; honesty of state) maps 1:1 — nothing added, nothing omitted |

## A2 — architecture claims (source §2)

| Claim | Verdict | Citation |
|---|---|---|
| Module map exists as listed | CONFIRMED | `src/` contains all listed modules incl. `state/{collect,diff,img4}.rs` and the three P3 stubs (`src/authorize.rs`, `src/execute.rs`, `src/verify.rs` — doc-comment-only, confirmed by head-of-file) |
| Guard 1 fails on `Command` outside `wrapper.rs` | CONFIRMED (live) | `scripts/ci_guards.sh:16-35` (boundary-anchored regex, hardened per the `ci-guards-regex-boundary-gaps` finding + self-test corpus); ran live: **OK** |
| Guard 2 fails on credential-shaped fields | CONFIRMED (live) | `scripts/ci_guards.sh:38-54` (matches `Option<T>`-wrapped fields per the vaulted Guard-2 widening); ran live: **OK** |
| Golden files freeze exact argv; silent change breaks build | CONFIRMED | `tests/fixtures/plans/*.json` (4 fixtures, exact `argv` + `authoritative_source`); `src/plan.rs:317-337` `assert_matches_golden_file` compares `plan()` output against committed fixtures with the literal message "plan output no longer matches the committed golden file" |
| BootState fields as listed (masked serial ≤4, sha384 96-hex, etc.) | CONFIRMED | `src/state/mod.rs:42-97`; serial rule `:105-108,145-149`; sha384 rule `:165-173`; shapes attributed to `spec/contract-spec.md` in module doc `:1-6` |
| `validate()` rejects, does not clamp | CONFIRMED | `src/state/mod.rs:125-188`; tests: `permissive_with_ssv_enabled_is_rejected`, `custom_kernel_outside_permissive_is_rejected`, `non_disjoint_other_container_is_rejected`, `bad_sha384_length_is_rejected`, `custom_boot_object_must_be_sep_signed`, `future_captured_at_is_rejected` (all in the 55-test run) |
| `PlannedTransition` pure data; no `Reduced <-> Permissive` edge; no-op needs nothing | CONFIRMED | `src/plan.rs:20` (doc: no `ReducedKexts <-> PermissiveCustomKernel` edge); `requires` = 1TR + owner credentials (`:121`, tests `:254-255`); no-op test asserts `!p.requires.owner_credentials` (`:313`) |
| Evidence bundle hash-chained and verifiable | CONFIRMED | `spec/contract-spec.md:37,90,137` (ValidReport: exit 0 requires every `invariants[].held == true`); bundle `evidence/vm-sec-research-25D125/`: `shasum -a 256 -c verify_permissive.sha256` → **verify_permissive.json: OK**; sub-bundles `reduced-baseline/` and `permissive-final/` each contain `report.json`+`report.sha256` |
| Exclusion of unstable outputs (twice-run diff = timestamp only) | CONFIRMED | `src/state/collect.rs:22,151` (module doc: `diskutil info` free-space / `ioreg` uptime-derived values excluded); the P1 twice-run gate |

⚠ **Overstatement in this section:** the brief says the worked example is
"`evidence/<session_id>/report.json` plus `report.sha256`". The real bundle is
structured: **two** session sub-bundles (`reduced-baseline/`, `permissive-final/`) each
with `report.json`+`report.sha256`, plus `baseline_reduced.json` and
`verify_permissive.json`+`.sha256` at the top level. Same claim, different shape — the
content-level claim (hash-chained, independently verifiable) holds.

## A3 — functional inventory (source §3)

| Claim | Verdict | Citation |
|---|---|---|
| `evaluate` read-only, twice-run diff = timestamp only | CONFIRMED | P1 gate; unstable-output exclusion above; doc-comment contracts |
| `plan` refuses from `Unknown` mode with exit 11 | CONFIRMED | `src/main.rs:23-25` `exit_code::PARSE_ERROR = 11`; multiple `:NSUTF`/fields — refusal paths all map to 11 (`:129-275`); test `unknown_mode_in_1tr_is_rejected` (`src/state/mod.rs:244-249`); golden-file tests |
| `verify` structural-diff only; invariant assertion is P3; `invariants: []` honest | CONFIRMED | `src/verify.rs:1-9` (assertion of global invariants deferred to P3 — "no meaningful implementation before `execute` exists in P3") |
| 1 MiB pre-read size cap on untrusted baseline JSON | CONFIRMED | `src/main.rs:35` `MAX_BASELINE_FILE_BYTES: u64 = 1024 * 1024`; test `oversized_baseline_file_is_rejected_before_parsing` (passed this run); source finding: `vuln_res/AUDIT.md` §1.2 |
| `apply`/`revert` stubs, non-zero exit, on purpose | CONFIRMED | `src/main.rs:112-116` ("not implemented: mutating subcommands require the P3/P4 authorize/execute/verify pipeline…") → `ExitCode::FAILURE` |
| Exit codes: `0`/`11` live; `10`/`13` spec-defined, unused | CONFIRMED | `src/main.rs:23-25` (only `OK`/`PARSE_ERROR` defined); `spec/contract-spec.md:151,156,165` (10 PreconditionNotMet, 13 InvariantViolated — never returned by read-only ops) |
| Build health: tests count recorded as 43 | **DRIFT: now 55** | `cargo test` this run: **55 passed, 0 failed**; tests were added since the 2026-11-10 recording (e.g. img4 real-manifest, oversized-baseline, wrapper non-zero-exit tests) — the *direction* of drift is good, the record is stale |
| clippy `-D warnings` + fmt clean | CONFIRMED (live) | both run this run: clean |
| PoC chain executed 2026-11-10 on VM; human-typed mutations; diff values | CONFIRMED | `evidence/vm-sec-research-25D125/README.md` (full narrative: release binary run on the tart VM; `bputil -g -k -v` / `bputil -f -v` / `bputil -n -c -s -v` typed live by the owner "exactly as golden rule 4 requires"; P3 pipeline did not run); recorded diff = `security_mode: Reduced → Permissive`, `ssv_enabled: true → false`, `allows_custom_kernel: false → true`; bundle hash verified above |

⚠ **Omission (not an error) in this section:** the brief's exit-code list omits
`12` (TransitionFailed, `spec/contract-spec.md:151`) and `14` (UnsupportedHost, `:143`)
— both are also spec-defined for the unbuilt mutating/host paths. The brief's
"specified for the unbuilt P3 mutator" framing covers them in spirit.

## A4 — vuln_res suite (source §4)

| Claim | Verdict | Citation |
|---|---|---|
| Seven agents under `.claude/agents/` | CONFIRMED | folder listing: `vulnres-recon, fuzz-harness, triage, exploit-dev, disclosure, environment-runner, orchestrator` (.md) — exactly seven |
| Scope enforced (own code+deps only, never Apple's platform) | CONFIRMED WITH CAVEAT | `vulnres-recon.md:9-13`: "Your scope contract is `vuln_res/CLAUDE.md` — read it first, every time" — enforcement is **by process instruction + scope contract doc**, not code; everywhere this matters (agent files, CLAUDE.md, plans/00 threat model) it is stated and cross-referenced, but nothing mechanically prevents a mis-configured agent run outside it — this is the honest boundary, not a defect of what was claimed |
| The two live `contains()` findings found+fixed | CONFIRMED | `vuln_res/sweep-reports/findings-index.md`: `ssv-enabled-contains-whole-blob` (9, fixed, 2026-11-10-001) and `security-mode-full-contains-whole-blob` (9, "fixed, confirmed against real VM-captured output", 2026-11-11-001) |
| Size-cap finding from `AUDIT.md` §1.2 | CONFIRMED | `vuln_res/AUDIT.md` §1 heading "### 1.2 `main.rs::cmd_verify` — `serde_json::from_str::<BootState>` on a user-supplied file"; fixed in code (`src/main.rs:35`) with test |
| Compound knowledge: indexed sweep-reports, plain-language on exploit-grade | CONFIRMED | `findings-index.md` (one row per finding, severity-first); `security-mode-full-contains-whole-blob.md` (score 9 = exploit-grade) has a prominent "## Short description" section in plain language; `knowledge/` = INDEX.md, structural facts (`build-test-clippy-fmt-clean-2026-11-10.md`, `environments/SCHEMA.md` etc.) |
| Disposition discipline (disposable envs, per-action approval, disclosure routing) | CONFIRMED WITH CAVEAT | `vulnres-recon.md:30-33` shows the discipline operating (ask before installing; record in knowledge); routing is defined in `spec/build-spec.md` golden rule 7 and the `vulnres-disclosure` agent — same caveat as above: process-anchored |

## Overstatements found (all minor; none invalidate the brief)

1. **"statically-linked"** (§1) — a direct restatement of the spec's deliverable text,
   not an independently verifiable property of the build config as written. Keep it
   attributed to `spec/build-spec.md:22`, not `Cargo.toml`.
2. **Evidence-bundle shape** (§2) — worked example is a *session directory with two
   sub-bundles + a verify diff*, not a single `report.json`. Verifiability claim holds
   (hash checked OK).
3. **Stale test count** (§3) — "43 tests" was the 2026-11-10 record; **55** pass today.
   Any downstream item assuming 43 should update.
4. **Exit-code list incompleteness** (§3) — omits spec-defined `12`/`14`.
5. **"confirm macOS by Finder.app presence"** (§2 environment gate) — confirmed
   (`src/env.rs:113` + logic `:54-60`), but the same detection also reports
   `bputil -d` failures through that path; the brief's framing is accurate but slightly
   tidier than the two-signal reality.

## Unverifiable from this checkout

- **"Twice-run diff = timestamp only" on real hardware** — the P1 gate is encoded in
  code and the exclusion logic exists, but the live proof was made on the VM session
  (2026-11-10). Re-running requires a real host or the same VM workflow.
- **`plan`'s `authoritative_source` freshness** — fixtures claim "confirmed on this
  host (bputil v0.1.14)"; verifying against Apple tool updates on newer builds needs a
  device sweep (`plans/phase-2.md`'s still-open architecture-doc item overlaps).
- **Mode meanings vs Apple's current semantics** — `A1.3` was confirmed against the
  code and spec, not against a live `bputil -h` on supported builds (no owned host in
  this session; golden-rule-compatible verification deferred).
- **Static-linkage property** — see A1 table caveat.

## What changed vs the brief's own framing

Nothing cosmetic surfaced as material. The audit **strengthens** the brief on the two
findings it cites (both live, both fixed, both test-backed) and **weakens it only on
record-keeping** (test count drift, bundle-shape description). The capability-audit
foundation for `gaps-roadmap.md` stands: everything §6 claims as a gap was re-confirmed
as a genuine gap (IMG4 not wired into `state::collect` — zero `img4` references in
`src/state/collect.rs` and `AUDIT.md` §1.1 independently notes the `dead_code` cfg;
`other_containers[].security_mode` hardcoded `Unknown` at `src/state/collect.rs:195`;
`security_mode` → `Unknown` degradation without sudo documented at `:12,228-259`).
