---
id: 2026-11-11-001-host-independent-parsing-hardening/security-mode-full-contains-whole-blob
target: state::collect::parse_security_mode (src/state/collect.rs:222, pre-fix)
source: real-data-verification (checked against an actual captured `bputil -d` output, not
  a hand-typed string)
status: fixed
score: 3 (reachability) x 1 (memory-safety-weight: logic-only) x 3 (blast radius) = 9
discovered_by: coordinating session, while reviewing `vuln_res/AUDIT.md` §2's existing
  "brittle text-parsing" finding against real `bputil -d` output captured earlier this
  project from a live VM (`progress/milestones.md` M8-M10)
sweep: ../INDEX.md#2026-11-11-001-host-independent-parsing-hardening
discovered_at: 2026-11-11
---

## Short description

`AUDIT.md` §2 already flagged `parse_security_mode`'s whole-blob `contains()` matching as
a *risk* — a hypothetical future wording change could misclassify `SecurityMode`. This
finding confirms it is **not hypothetical**: against this project's own real, captured
`bputil -d` output from a live VM, the `Full` branch's check never matches at all, because
it requires an exact single space (`"security mode: full"`) and Apple's real output
column-pads with many spaces (`"Security Mode:               Full       (smb0): absent"`).
A genuinely `Full`-security host silently degrades to `SecurityMode::Unknown` — not a
dangerous wrong-permission misclassification (fails closed, same as a parse error), but a
correctness bug that breaks the tool on the single most common state every Apple Silicon
Mac ships in. `Reduced`/`Permissive` happened to keep working only because their checks are
simple substring tests that don't care about the padding — same underlying bug class, just
not yet visible for those two values.

## Technical detail

`src/state/collect.rs`, pre-fix:

```rust
fn parse_security_mode(bputil_output: &str) -> SecurityMode {
    let lower = bputil_output.to_lowercase();
    if lower.contains("security mode: full") || lower.contains("security mode (csec): 0") {
        SecurityMode::Full
    } else if lower.contains("permissive") {
        SecurityMode::Permissive
    } else if lower.contains("reduced") {
        SecurityMode::Reduced
    } else {
        SecurityMode::Unknown
    }
}
```

Two independent problems, both confirmed against real data:

1. **Spacing.** `"security mode: full"` (one space) is not a substring of
   `"security mode:               full       (smb0): absent"` (many spaces, Apple's own
   column alignment). No amount of real-world output would ever satisfy this exact literal.
2. **The `(CSEC): 0` fallback never fires either.** Real output's numeric line reads
   `"Security Mode                           (CSEC): 1"` — `CSEC` was `1` in every state
   this project captured (`Full`, `Reduced`, `Permissive` alike; see the three
   `_VM_VIRTUALIZED` fixtures added in this same sweep), so the `(csec): 0` check is
   checking for a value that doesn't actually distinguish `Full` from anything else, on top
   of also having the same spacing mismatch as problem 1.

Net effect: there is currently no real `bputil -d` output this function can classify as
`Full` at all.

## Reproduction

Proven against real data, not a synthetic string — `tests/fixtures/bputil_d_full_VM_VIRTUALIZED.txt`
is an actual `sudo bputil -d` capture (over SSH) from a live VM in a genuinely `Full`
security state:

```
$ cargo test state::collect::tests::parses_real_full_state_from_vm_capture
```

Against the pre-fix implementation, this assertion (`parse_security_mode(fixture) ==
SecurityMode::Full`) fails — the function returns `SecurityMode::Unknown` instead.

## Classification

- **Type:** logic-divergence (silent wrong value — degrades to `Unknown`, does not panic
  or misreport a *different* valid mode)
- **Reachability:** 3 — every `collect()` call on a host (or VM) actually in `Full`
  security, which is the out-of-the-box default for every Apple Silicon Mac
- **Blast radius:** 3 — `security_mode` is the one field `plan()` (`src/plan.rs:83`) uses
  to decide which transitions are legal; `Unknown` causes `plan()` to refuse everything
  (`PlanError::UnknownFromMode`), meaning the tool's planner is non-functional against the
  single most common starting state it will ever be run against. Not a dangerous
  misauthorization (fails closed, same as any other parse failure), but a severe
  correctness/availability bug for exactly the claim this sweep set out to establish:
  that the tool works "regardless of host."

## Chaining notes

Checked against the two already-documented instances of this bug class
(`env.rs:72`'s 1TR-pairing check, and the `(CSEC)`-line ambiguity this same fix also
resolves — see below): independent read sites, no composable chain. The `(CSEC)`-line
ambiguity is not a separate finding but the same root cause (`contains("security mode")`
not distinguishing *which* of `bputil -d`'s two "Security Mode" lines it's looking at) —
documented together here rather than filed twice.

## Resolution

**Fixed directly**, following `vulnres-disclosure`'s Case A process (same posture as the
`ssv-enabled-contains-whole-blob` finding from the prior sweep):

- `parse_security_mode` now anchors to the one line containing `"security mode:"` (colon
  immediately after "mode" — present only on the human-readable summary line, never the
  numeric `(CSEC)` line, which has many spaces before its own colon), extracts the text
  between that colon and the next `(`, trims and lowercases it, and exact-matches
  `"full"`/`"reduced"`/`"permissive"` — same anchored-line discipline as
  `extract_volume_group`/`extract_serial_masked`/`parse_ssv_enabled` already use in this
  file.
- Three real fixtures added — `tests/fixtures/bputil_d_{full,reduced,permissive}_VM_VIRTUALIZED.txt`
  — two captured directly over SSH, one transcribed from a screenshot of the VM's recovery
  Terminal (recoveryOS has no SSH to capture through; see `tests/fixtures/README.md`'s new
  `_VM_VIRTUALIZED` section for full provenance and chain of custody). These fill a gap
  `tests/fixtures/README.md`'s own "What's missing" section had flagged since this
  project's P0 phase.
- Four regression tests added: one per fixture (`parses_real_{full,reduced,permissive}_state_from_vm_capture`)
  plus `the_numeric_csec_line_is_never_mistaken_for_the_summary_line`, which isolates the
  line-selection half of the fix on its own.
- Verified: `cargo test` 55/55 passing (up from 49), `cargo clippy --all-targets -- -D
  warnings` clean, `cargo fmt --check` clean.
