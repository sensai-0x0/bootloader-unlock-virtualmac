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
