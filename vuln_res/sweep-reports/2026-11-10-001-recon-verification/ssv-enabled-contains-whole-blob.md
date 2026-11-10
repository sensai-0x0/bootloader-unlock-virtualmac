---
id: 2026-11-10-001-recon-verification/ssv-enabled-contains-whole-blob
target: state::collect::collect (src/state/collect.rs:84)
source: static-analysis
status: fixed
score: 3 (reachability) x 1 (memory-safety-weight: logic-only) x 3 (blast radius) = 9
discovered_by: vulnres-recon (run directly by the coordinating session; see sweep summary)
sweep: ../INDEX.md#2026-11-10-001-recon-verification
discovered_at: 2026-11-10
---

## Short description

The code that decides whether System Security Verification (SSV) is turned on just
checks whether the word "enabled" appears **anywhere** in a system tool's entire output,
instead of looking at the one line that actually says so. Today's real-world wording
happens not to trip this up, but there's no safety net if that wording ever changes —
unlike two very similar, already-documented issues in this same file, this one has no
fallback at all: if the check ever misreads the output, it just silently decides "SSV is
off" with no error, no warning, nothing. This feeds directly into the tool's core
security read, `evaluate`, which every other command depends on.

## Technical detail

`src/state/collect.rs:84`:

```rust
let ssv_record = wrapper::run(&["csrutil", "authenticated-root", "status"])?;
let ssv_enabled = ssv_record.stdout.to_lowercase().contains("enabled");
```

This is the same class of bug `vuln_res/AUDIT.md` §2 already documented at `env.rs:72`
and `state/collect.rs:203-208` (substring-matching a security-relevant fact against raw
CLI output instead of an anchored, structured parse) — but this third instance is worse
on two counts the audit missed:

1. **No fail-closed branch exists at all.** `env.rs:72`'s version has an `else` that
   returns `UnconfirmedRecoveryVariant` on anything it doesn't recognize —
   `parse_security_mode` (`collect.rs:203-208`) at least falls through to `Unknown` on no
   match. This line is a bare boolean with no error path whatsoever: whatever the output
   is, `ssv_enabled` gets *some* value, silently, every time.
2. **Higher reachability than either documented instance.** `img4::parse_manifest_der`
   (`AUDIT.md` §1.1) isn't even wired into production yet. This line runs on every single
   call to `collect()` — which `evaluate`, `plan`, `verify`, and `report` all call. It's
   about as reachable as code in this binary gets.

Today's real `csrutil authenticated-root status` output ("...status: enabled" /
"...status: disabled") happens not to collide — "disabled" does not contain "enabled" as
a substring. That's a fact about today's specific wording, not a property the code
enforces. Any future macOS build adding, e.g., a deprecation notice or help text that
happens to contain the word "enabled" in an unrelated sentence would silently flip this
value with zero signal that anything went wrong.

## Reproduction

Not fuzzer-confirmed (this is a `static-analysis`-sourced finding, not a fuzz crash —
there is no "crash" to reproduce; the risk is a silent wrong value, which is a design
review finding, exactly like `AUDIT.md`'s other two `contains()` instances). To see the
risk directly:

```
$ cat <<'EOF' | rustc --edition 2024 -
fn main() {
    let hypothetical_future_output = "Authenticated Root status: disabled\n(Note: root filesystem signing can be enabled via csrutil enable)";
    println!("{}", hypothetical_future_output.to_lowercase().contains("enabled")); // true — wrong
}
EOF
```

## Classification

- **Type:** logic-divergence (silent wrong value, no crash)
- **Reachability:** 3 — every `collect()` call, i.e. every CLI subcommand except `apply`/`revert` (unimplemented)
- **Blast radius:** 3 — `ssv_enabled` is part of `TargetContainer`, directly checked by `contract-spec.md`'s invariant that `ssv_enabled == false` whenever `security_mode == Permissive` (see `src/plan.rs:179`'s comment citing exactly this)

## Chaining notes

Checked: does this compose with the other two documented `contains()` instances
(`env.rs:72`, `collect.rs:203-208`) for greater impact? No — all three are independent
read sites feeding different fields (`Environment`, `SecurityMode`, `ssv_enabled`
respectively); a wrong value in one doesn't amplify a wrong value in another. Each is an
independent instance of the same *pattern*, not a composable chain. Recorded as checked,
not skipped.

## Resolution

**Fixed directly** (commit pending — not yet pushed as a PR; applied in-session at the
user's explicit request to "make the change," following `vulnres-disclosure`'s Case A
process even though that agent itself isn't invokable yet this session — see
`agent-registry-not-live-this-session.md`):

- Added `parse_ssv_enabled(csrutil_output: &str) -> Option<bool>` to
  `src/state/collect.rs`, anchored to the one line containing `"status"`, exact-matching
  `"enabled"`/`"disabled"`, returning `None` (fail closed) on anything else — same
  discipline as `extract_volume_group`/`extract_serial_masked` in the same file.
- Added `CollectError::NoSsvStatus(String)`; `collect()` now propagates this as a real
  error instead of silently defaulting `ssv_enabled` to a guessed value, matching how
  `NoVolumeGroup`/`NoSerial` already fail the whole `collect()` call rather than guess.
- Five regression tests added, including one against the real captured fixture
  (`tests/fixtures/csrutil_authenticated_root_status.txt`) and one
  (`trailing_unrelated_text_does_not_flip_the_anchored_result`) that specifically
  reproduces the scenario this finding describes — the old `.contains("enabled")`
  implementation would have returned `true` (wrong) against it; the fix correctly
  returns `Some(false)`.
- Verified: `cargo test` 49/49 passing (up from 44), `cargo clippy --all-targets -- -D
  warnings` clean, `cargo fmt --check` clean.

Not yet committed to git — the diff is in the working tree, uncommitted, pending the
user's review/commit decision (this repo's workflow is "ask before committing" unless
told otherwise).
