# Evidence bundle — `vm-sec-research-25D125`, Full → Reduced → Full → Permissive

Produced 2026-11-10 against `vm-sec-research-25D125` (a `tart` VM built from an IPSW
matching this host's own chip/macOS build, `26.3`/`25D125` — see `progress/milestones.md`
M8/M9/M6 for the full narrative). Every file here was produced by the real
`bputil-eval` binary (release build, copied onto the VM and run there over SSH — never
simulated, hand-built, or reconstructed from memory), run against the live guest.

## Contents

- `reduced-baseline/report.json` + `.sha256` — `bputil-eval report` output captured while
  the container was in `Reduced` security mode (third-party kexts enabled, reached via a
  live, human-typed `bputil -g -k -v <vuid>` from the VM's recovery/1TR-equivalent
  environment).
- `baseline_reduced.json` — the `bputil-eval evaluate --json` output for that same
  `Reduced` state, used as the `--baseline` input to `verify` below. (Note: the VM's own
  on-disk copy of this file did not survive the two subsequent reboots through recovery —
  see `progress/milestones.md`'s log for 2026-11-10 for that finding. This copy was
  recovered from this session's own captured terminal log, not re-derived or guessed, and
  its hash matches the `evaluate --json` output as originally printed.)
- `permissive-final/report.json` + `.sha256` — `bputil-eval report` output captured after
  a second live mutation: revert to `Full` (`bputil -f -v <vuid>`), then
  `bputil -n -c -s -v <vuid>` to reach `Permissive` (custom-kernel-capable, SSV and kernel
  CTRR disabled) — again both run live, by the device's owner, from the VM's recovery
  environment, never scripted by this session.
- `verify_permissive.json` + `.sha256` — `bputil-eval verify --baseline
  baseline_reduced.json --json`, the tool's own structured diff between the `Reduced`
  baseline and the fresh `Permissive` measurement:
  ```
  target_container.security_mode:       Reduced -> Permissive
  target_container.ssv_enabled:         true -> false
  target_container.allows_custom_kernel: false -> true
  ```

## Verifying this bundle yourself

```bash
shasum -a 256 -c reduced-baseline/report.sha256   # run from inside reduced-baseline/
shasum -a 256 -c permissive-final/report.sha256   # run from inside permissive-final/
shasum -a 256 -c verify_permissive.sha256
```

All three were confirmed matching when this bundle was assembled.

## What this is, and isn't, evidence of

This is evidence that **this project's custom toolchain, driving `bputil`/`csrutil`, and
this project's own `bputil-eval evaluate`/`verify`/`report`, correctly measured a real
`SecurityMode` transition on a real (if virtualized) Apple Silicon boot-security surface**
— not evidence of a signature bypass, SEP manipulation, or anything outside the
`Full → Reduced/Permissive` spectrum this toolchain targets. See `progress/goal.md`'s "What 'unlocked' means
here" section and `reports/unlocked-bootloader-evidence.md` for the precise scope of that
claim. `bputil-eval`'s own `authorize`/`execute`/`verify.assert_invariants` pipeline (P3)
did not run any of this — the mutating `bputil` commands were typed live by the VM's owner,
exactly as golden rule 4 requires.
