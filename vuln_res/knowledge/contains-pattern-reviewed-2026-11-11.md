---
name: contains-pattern-reviewed-2026-11-11
type: parsing-pattern
description: full suite-wide re-derivation of security-relevant .contains() sites per 01-static-analysis-and-dependency-agent.md §1.3 — no third instance beyond AUDIT.md's two found; posture_confidence introduces no new text-parsing
updated: 2026-11-11
---

Traced every `wrapper::run(...)` call site (`src/env.rs:56,92,93`;
`src/state/collect.rs:112,116,124,128,135`) and followed each `CommandRecord.stdout`
flow to its consumer, per `../plans/01-static-analysis-and-dependency-agent.md` §1.3's
procedure — not just re-citing `../AUDIT.md`'s two named instances.

**Result: still exactly two sites that decide a security-relevant enum via `.contains()`
on CLI output, same two `AUDIT.md` §2 already named, no third found anywhere else in the
tree:**

1. `src/env.rs:72` (`os_type_line.to_lowercase().contains("one true recoveryos")`) —
   unchanged, still open, still the lower-priority item (anchored to one found line
   already; the risk is a hypothetical future wording collision, not a confirmed-broken
   check — see [[../sweep-reports/2026-11-11-001-host-independent-parsing-hardening/summary]]'s
   "Not done, and why").
2. `src/state/collect.rs::parse_security_mode` — fixed in the prior sweep
   ([[../sweep-reports/2026-11-11-001-host-independent-parsing-hardening/security-mode-full-contains-whole-blob]]);
   now anchors to the one line containing `"security mode:"` and exact-matches the
   extracted value, with a fail-closed `Unknown` default.

`parse_ssv_enabled` (`src/state/collect.rs:263`) also uses `.contains()`, but only to
*find* the one relevant line (`.find(|l| l.to_lowercase().contains("status"))`), then
exact-matches the trimmed value after the colon — already anchored, already has a
fail-closed `None` branch (fixed in
[[../sweep-reports/2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob]]).
Not a new instance of the risky pattern.

`extract_serial_masked`, `extract_volume_group`, `extract_other_containers` all use
`.contains()`/`.find()` only to locate the relevant line of non-security-relevant,
informational text (serial, volume group UUID) — out of this check's scope by the plan's
own definition ("feeding `Environment`, `SecurityMode`, or ... `is_mutation_allowed()`").

**The new `posture_confidence` derivation code
(`src/state/collect.rs::derive_posture_confidence`, `src/state/mod.rs::PostureConfidence`)
introduces no new text-parsing at all** — it's a pure function over an already-parsed
`SecurityMode` plus a 3-variant `BputilOutcome` enum computed from `Result`/`exit_code`
matching, not string matching. It does *not* have the brittle-parsing bug class. It did,
however, have a different bug from the same "security-relevant signal silently dropped"
family — see
[[../sweep-reports/2026-11-11-002-posture-confidence-recon/posture-confidence-missing-from-diff]]
(fixed this sweep): `state::diff::diff` never compared `posture_confidence` at all, so a
confidence-only change between two `BootState`s produced zero diff entries.

A future sweep: re-run this trace whenever `collect.rs`/`env.rs` gains a new
`wrapper::run` call site (P3's `authorize`/`execute`/`verify` will add several) — don't
assume "still just these two" without re-checking once mutation-path parsing exists.
