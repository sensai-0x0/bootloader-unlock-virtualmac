# Fallback ("ordinary") recoveryOS is likely a real-hardware-only concept

**Learned:** 2026-11-11, researching whether a `tart` VM could produce a confirmed
fallback-recovery environment to resolve the `env-1tr-fallback-detection-confirmed-broken`
finding.

## The mechanism (sourced, not guessed)

On Apple Silicon, "fallback"/"ordinary" recoveryOS is a **second, physically separate copy
of recoveryOS** stored in its own hidden APFS container (`Apple_APFS_Recovery`) on the
internal SSD — distinct from the paired Recovery volume that lives in the main boot volume
group alongside the OS it's paired to.

- [Apple's Platform Security Guide](https://support.apple.com/guide/security/secac71d5623)
  describes it as "a second copy of recoveryOS kept for resiliency."
- [Asahi Linux's boot-mode documentation](https://asahilinux.org/docs/fw/boot/)
  independently uses the same "1TR" / "ordinary recoveryOS" vocabulary this project does,
  and confirms the SEP rejects boot-policy edits (error 11, "AP boot mode") outside 1TR —
  i.e. fallback recovery genuinely cannot run `bputil`'s mutation path at all, by design.
- [eclecticlight.co's history of Recovery Mode](https://eclecticlight.co/2026/11/07/a-brief-history-of-recovery-mode/)
  and its [2021 piece on the third recovery mode](https://eclecticlight.co/2021/05/31/m1-macs-have-a-third-recovery-mode/)
  describe the trigger: a **single** power-button press reaches paired/1TR recovery; a
  **double press, held through the second press**, reaches fallback. This is a Boot
  ROM-level gesture, not a software setting — no CLI tool (`bputil`, `csrutil`, `nvram`)
  exposes a parameter for it.

## Why this likely rules out VM experimentation

No source found — including [cua.ai's Lume docs](https://cua.ai/docs/concepts/how-sip-works-in-lume-vms),
the closest comparable VM-tooling documentation found — describes a second, fallback
recovery container existing in a Virtualization.framework VM's disk image. Lume's own
description is one disk image holding exactly macOS + (one) Recovery + one LocalPolicy.
Tart's `--recovery` flag uses Apple's public `VZ` "boot into recovery" API (new in
Ventura), which is a single mode — there's no documented API surface for simulating the
Boot-ROM-level double-press gesture inside a guest.

## How to use this

Treat any future "let's just test it in the VM" instinct for this specific question with
this writeup in mind: the blocker isn't effort, it's that the VM format likely has no
second recovery container to boot into in the first place. Closing
`env-1tr-fallback-detection-confirmed-broken` for real needs either the project's
still-missing companion architecture document, or testing on real scratch hardware with a
physical double-press — a different, higher-risk track (`spec/phased-plan.md`'s P3) than
this project's VM research, and not something to attempt by guessing at a VM-side
workaround.
