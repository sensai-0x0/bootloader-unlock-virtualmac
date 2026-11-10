---
id: 2026-11-11-003-license-policy-and-1tr-detection-gap/env-1tr-fallback-detection-confirmed-broken
target: env::detect (src/env.rs:72, fallback branch)
source: real-data-verification (checked against this project's own real
  `bputil -d` captures, not a hand-typed string)
status: escalated, not fixed — documented and test-covered; research now indicates this
  is likely unresolvable via VM experimentation at all (see "Research update" below),
  not just "not yet attempted"
score: n/a — this is a fail-closed functional gap (blocks a future capability), not a
  vulnerability; scoring it as 0 reachability toward overclaiming would misrepresent it,
  so it's left unscored like the other operational entries in this index
discovered_by: coordinating session, re-examining `vuln_res/AUDIT.md` §2's "speculative"
  framing of `env.rs:72` against this project's own `tests/fixtures/bputil_d_*_VM_VIRTUALIZED.txt`
  fixtures (added in the 2026-11-11-001 sweep) while fixing an unrelated `cargo deny`
  license-policy gap
sweep: ../INDEX.md#2026-11-11-003-license-policy-and-1tr-detection-gap
discovered_at: 2026-11-11
---

## Short description

`vuln_res/AUDIT.md` §2 flagged `env.rs:72`'s `.contains("one true recoveryos")` check as a
*speculative* risk — a hypothetical future wording change *might* cause a false positive.
This finding upgrades that from speculative to **confirmed**, and in the opposite direction
than originally worried about: against this project's own real `bputil -d` captures
(`tests/fixtures/bputil_d_{full,reduced,permissive}_VM_VIRTUALIZED.txt`), the "OS Type"
line reads `"macOS (overriden)"` in **every** captured state — including
`bputil_d_permissive_VM_VIRTUALIZED.txt`, captured from an environment independently
confirmed to be paired 1TR recovery (`whoami` returned `root` with no login, and
`/System/Library/CoreServices/Finder.app` was absent — a different, independent signal
than this check itself). The string `"one true recoveryOS"` never occurs. The fallback
branch, as written, cannot currently classify anything as `OneTrueRecovery` — ever,
against this real tool version.

## Technical detail

`src/env.rs`'s `detect()`, fallback branch (reached whenever `Finder.app` is absent):

```rust
let os_type_line = record.stdout.lines().find(|line| line.contains("OS Type")).unwrap_or("");
if os_type_line.to_lowercase().contains("one true recoveryos") {
    Ok(Environment::OneTrueRecovery)
} else {
    Err(EnvError::UnconfirmedRecoveryVariant { detail: os_type_line.to_string() })
}
```

Real captured `OS Type` lines, across every state this project has ever measured:

```
OS Type                                       : macOS (overriden)
```

`is_mutation_allowed()` (`env.rs`) is `matches!(detect(), Ok(Environment::OneTrueRecovery))`
— so this gap means `is_mutation_allowed()` is unconditionally `false` whenever
`Finder.app` is absent, on this real tool version. **This is the single gate
`authorize`/`execute` (P3, not yet implemented) are required to consult before any
mutation.** As written, once P3 is built, it would never be able to authorize a mutation
on any real hardware or VM running this `bputil` version — not a security hole (fails
closed, the safe direction per golden rule 1), but a confirmed functional dead end.

## Reproduction

`src/env.rs::tests::real_os_type_line_from_a_confirmed_paired_1tr_environment_does_not_match`
(new in this sweep) proves it directly: feeds the real, independently-confirmed-paired
fixture's `OS Type` line through the extracted `is_one_true_recovery_os_type_line` function
and asserts it returns `false` — annotated as documenting *current, confirmed* behavior,
not desired behavior, so a future fix that actually closes this gap will make the test fail
loudly rather than silently "break" something that was never working.

## Classification

- **Type:** functional gap in a security-critical gate (fails closed, not a vulnerability)
- **Reachability:** would be total, once P3 exists — every `authorize`/`execute` call
- **Blast radius:** blocks the capability entirely rather than misauthorizing anything;
  the direction of failure is safe, which is why this isn't scored as a vulnerability

## Resolution

**Deliberately not fixed with a new matching string** — this project's own standing
discipline (every parsing fix in `vuln_res/sweep-reports/` so far) is "confirmed, not
guessed," and no alternative text that actually distinguishes paired 1TR from ordinary
fallback recovery has been confirmed. Inventing one here would repeat exactly the mistake
this finding exists to catch.

What was done instead:

- `src/env.rs`'s module doc comment and the fallback branch's inline comment rewritten to
  state the confirmed finding plainly, with evidence citations, superseding the earlier
  "should be validated... before P3 ships" speculative framing.
- The matching logic extracted into a pure, directly-testable function
  (`is_one_true_recovery_os_type_line`), with a regression test proving the confirmed-gap
  behavior against real fixture data rather than leaving it as an unverified prose claim.
- This finding written up, so the gap has a permanent, indexed record rather than living
  only in a doc comment someone could miss.

**What would actually close this** (not attempted — needs real research, not more code):
either the still-missing companion architecture document (`CLAUDE.md`'s long-standing open
item), or deliberate VM-based research to capture what a confirmed **fallback** (non-paired)
recovery environment's `bputil -d` output actually looks like, to find a real distinguishing
signal — `tart`'s recovery boot (used for the `_VM_VIRTUALIZED` fixtures) has so far only
ever produced the confirmed-paired case; producing a confirmed-*un*paired case to compare
against hasn't been attempted and may not even be possible without real hardware.

Verified: `cargo test` 64/64 (up from 63), `cargo clippy --all-targets -- -D warnings`
clean, `cargo fmt --check` clean, `./scripts/ci_guards.sh` green.

## Research update (2026-11-11, same day, follow-up)

The user asked to pursue the "VM-based research" option above. Before attempting any
destructive VM experiment, researched the actual mechanism (web search, not guessed) —
see `vuln_res/knowledge/fallback-recoveryos-is-likely-real-hardware-only.md` for the full
sourced writeup. Summary of what changes this finding's outlook:

- **Fallback ("ordinary") recoveryOS is a second, physically separate copy of recoveryOS**
  stored in its own hidden APFS container (`Apple_APFS_Recovery`) on the internal SSD —
  distinct from the paired Recovery volume in the main boot volume group. Confirmed via
  Apple's own Platform Security Guide and independently corroborated by Asahi Linux's
  boot-mode documentation, which uses the same "1TR" vs. "ordinary recoveryOS" vocabulary
  this project does.
- **It's triggered by a Boot ROM-level gesture** — a double-press-and-hold of the power
  button, distinct from the single press that reaches paired/1TR recovery — not a software
  setting, not something `bputil`, `csrutil`, or any userspace tool exposes a parameter
  for.
- **No source found confirms a tart/Virtualization.framework VM can produce this at all.**
  The closest technical documentation found (for a comparable VM tool, Lume) describes a
  VM's disk image as holding exactly one macOS+Recovery pairing with one LocalPolicy — no
  mention of a second, fallback recovery container. Tart's own recovery-boot feature uses
  Apple's public `VZ` "boot into recovery" API, which is a single mode with no documented
  way to simulate the hardware-level double-press gesture.

**Conclusion: this is very likely a real-hardware-only distinction, not something a
disposable VM can be made to produce.** Downgrading this from "needs VM research" to
"needs real scratch hardware, per `spec/phased-plan.md`'s P3 track — a different, higher-
risk undertaking than this project's VM work, not attempted here." No VM experiment was
run — the research above was judged sufficient to avoid a likely-futile and non-trivial
destructive attempt (corrupting a VM's Recovery container, with no confirmation the VM
format even has room for the second container being corrupted).
