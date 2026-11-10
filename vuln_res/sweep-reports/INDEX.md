# Sweep ledger

One entry per sweep, ever run. Append, never rewrite history.

## 2026-11-10-001-recon-verification

- **Agents run:** `vulnres-recon`'s procedure (run directly by the coordinating session —
  the agent type isn't yet live in this session's registry, see that sweep's
  `agent-registry-not-live-this-session.md`)
- **Environment(s):** none (static analysis only, no sandbox needed)
- **Targets covered:** full `src/` tree — build, test, clippy, fmt, CI guards, and an
  independent re-derivation of every `contains()`/`Command::`/credential-shaped-field
  pattern, not just a re-citation of `../AUDIT.md`
- **Duration:** a few minutes
- **New findings:** 2 — [`ssv-enabled-contains-whole-blob`](./2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob.md)
  (score 9, the highest-scored static finding so far — **fixed in this same sweep**, 5
  regression tests added, `cargo test`/`clippy`/`fmt` all clean, uncommitted pending
  review) and
  [`agent-registry-not-live-this-session`](./2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md)
- **New knowledge entries:** 4 — see [`summary.md`](./2026-11-10-001-recon-verification/summary.md)
- **Blocked on / escalated to human:** `cargo audit`/`cargo deny` install approval still
  pending; the `vulnres-*` agent registry gap needs a fresh session to confirm resolved

## 2026-11-10-002-fallback-and-audit

- **Agents run:** `vulnres-recon`'s procedure (via the documented fallback — see
  `../plans/06-orchestration-and-scheduling.md`)
- **Environment(s):** none (static analysis + one approved host-level tool install)
- **Targets covered:** re-confirmed the agent-registry gap in a fresh session and
  root-caused it (global-only `~/.claude/agents/` loading); ran the now-approved
  `cargo audit`; re-walked all three security-relevant `.contains()` call sites for a
  fail-closed branch
- **Duration:** well under an hour
- **New findings:** 0 (closed/root-caused the existing `agent-registry-not-live-this-session`
  finding instead)
- **New knowledge entries:** 1 updated — see
  [`summary.md`](./2026-11-10-002-fallback-and-audit/summary.md)
- **Blocked on / escalated to human:** none remaining from this sweep — the registry gap
  is now a filed harness-feedback item with a working fallback, not an open blocker

## 2026-11-11-001-host-independent-parsing-hardening

- **Agents run:** none (run directly by the coordinating session — no agent registry
  dependency, per the documented fallback)
- **Environment(s):** none (static analysis + real fixture data, no sandbox needed)
- **Targets covered:** `vuln_res/AUDIT.md`'s three open, no-host-install-required findings
  (§1.2 verify DoS, §2 brittle text-parsing, §3 CI guard regex gaps); §1.1 and §4
  deliberately excluded (need `cargo-fuzz`/`cargo-audit` installed — stopped to ask first,
  not attempted)
- **Duration:** under an hour
- **New findings:** 3 — [`security-mode-full-contains-whole-blob`](./2026-11-11-001-host-independent-parsing-hardening/security-mode-full-contains-whole-blob.md)
  (score 9, confirmed against real VM-captured `bputil -d` output, not hypothetical — **fixed
  in this same sweep**, 4 new regression tests + 3 new real fixtures),
  [`verify-baseline-no-size-cap`](./2026-11-11-001-host-independent-parsing-hardening/verify-baseline-no-size-cap.md)
  (score 2, **fixed**, 2 new tests), and
  [`ci-guards-regex-boundary-gaps`](./2026-11-11-001-host-independent-parsing-hardening/ci-guards-regex-boundary-gaps.md)
  (operational, **fixed**, new `scripts/ci_guards_selftest.sh`)
- **New knowledge entries:** see [`summary.md`](./2026-11-11-001-host-independent-parsing-hardening/summary.md)'s "New knowledge" section
- **Blocked on / escalated to human:** none — all three targeted findings fixed; §1.1/§4
  left for the user to approve a host-level tool install before attempting

## 2026-11-11-002-posture-confidence-recon

- **Agents run:** `vulnres-recon`'s procedure (`../plans/01-static-analysis-and-dependency-agent.md`)
- **Environment(s):** none (static analysis + already-approved `cargo audit`/`cargo deny`,
  no new host-level install)
- **Targets covered:** full suite-wide re-derivation of security-relevant `.contains()`
  flows (not just `AUDIT.md`'s two named instances — specifically checked whether the new
  `posture_confidence` schema work, commits `a0cdd5e`/`20da5e6`, introduces a third);
  `cargo clippy`/`cargo fmt`/`cargo test`/both CI guard scripts re-confirmed clean; a fresh
  `cargo audit` run plus a first-ever `cargo deny check` against this repo's `Cargo.lock`
- **Duration:** under an hour
- **New findings:** 1 —
  [`posture-confidence-missing-from-diff`](./2026-11-11-002-posture-confidence-recon/posture-confidence-missing-from-diff.md)
  (score 6, **fixed in this same sweep**: `state::diff::diff` never compared the new
  `posture_confidence` field, silently defeating the field's own stated purpose —
  "surface unmeasured louder" — whenever a comparison's other fields happened to match;
  one new regression test added)
- **New knowledge entries:** 3 — build/test/clippy/fmt/guards re-confirmed clean at
  `20da5e6`; the `.contains()` suite-wide trace confirmed no third instance and that
  `posture_confidence` itself introduces no new text-parsing; `cargo audit` re-run clean
  against a fresher advisory snapshot and `cargo deny check` run for the first time
  (license-policy config gap found, not a vulnerability — see knowledge entry)
- **Blocked on / escalated to human:** none new. `AUDIT.md` §1.1 (DER fuzz harness) still
  needs `cargo-fuzz`, not installed, not attempted. The `cargo deny` license-policy gap
  (missing `deny.toml`) is a recommendation, not fixed — it would live at the repo root,
  outside this task's scoped write directories.
