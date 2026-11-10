# Evidencing an "Unlocked" Bootloader via a Host-Matched-Chipset VM

**Report date:** 2026-11-10
**Source material:** `progress/goal.md`, `progress/milestones.md`, `plans/research-environment.md`, `spec/contract-spec.md`

This report exists to pin down one specific, easy-to-misread question precisely: what would actually count as evidence that a virtual Mac's bootloader has been "unlocked" by this project, and why the virtual machine's chip generation has to match (or be older than) the host's own chip generation before that evidence can even be attempted.

## 1. What "unlocked" means here — and what it does not

`progress/goal.md` defines this term exactly once, deliberately, because the phrase invites misreading:

> "Unlocked" has exactly one meaning in this project: `spec/contract-spec.md`'s `SecurityMode` moving away from `Full` to `Reduced` or `Permissive`. It does not mean bypassing a signature check, defeating the Secure Enclave, or touching a device or VM the person running this project doesn't own or control.

Concretely, this is the security-policy spectrum this project's custom toolchain targets:

| `SecurityMode` | What it allows | How it's reached |
|---|---|---|
| `Full` | Baseline boot security | — |
| `Reduced` | Third-party kernel extensions | `bputil -m -u` (owner-authorized, inside 1TR) |
| `Permissive` | A custom/unsigned kernel | `bputil -m -n -u` + `kmutil configure-boot -c` (owner-authorized, inside 1TR) |

A virtual machine this project creates and controls is still, for this purpose, a device whose *only* legitimate path between these states is this project's custom toolchain driving `bputil`/`kmutil`/`csrutil`, exercised by the VM's own equivalent of an owner physically present and authorizing inside its own One True Recovery (1TR) environment. Nothing in this research track, and nothing in `bputil-eval` itself, attempts a signature bypass, SEP manipulation, or any other route around that gate. "Evidencing an unlock" means *measuring that the toolchain reports the change*, never engineering around it to produce the appearance of one.

"Verifying" likewise means a fresh measurement, not an assumption: the success condition for this entire track is `bputil-eval evaluate`/`verify` actually reporting the new `SecurityMode`, not a plan having been generated or a command having been attempted. This is golden rule 8 from `spec/build-spec.md`, applied to this project's own research with the same weight it applies to the tool it builds.

## 2. The four-step evidence chain

`progress/goal.md`'s "What success looks like" section specifies exactly what a complete evidence bundle requires, against a VM this project built and controls:

1. `evaluate` reporting `security_mode: Full` as the baseline — a fresh measurement, not an assumed starting state.
2. `plan` producing a transition to a target profile (`Reduced` or `Permissive`).
3. The VM's own equivalent of 1TR, with its own owner-present authorization, actually running `apply`.
4. `evaluate`/`verify` run again, reporting the new, non-`Full` `security_mode` — again a fresh measurement, not an inference from step 3 having been attempted.

If step 3 turns out to be technically impossible inside a VM — for instance, if SEP/LocalPolicy communication genuinely fails inside a virtualized guest, as community reports have suggested — the honest outcome is a clearly written, evidenced finding to that effect, plus an explicit decision about whether to pursue the same four-step proof on real scratch hardware instead (`spec/phased-plan.md`'s P3). A failure to produce the chain is itself a valid, useful research result; fabricating step 4 from a hand-built fixture pretending to be a live measurement is explicitly ruled out.

**Update, 2026-11-10 (after this report's original writing): all four steps have now been
executed, twice, against a real VM** — see `progress/milestones.md`'s M8/M9/M10 log
entries and `evidence/vm-sec-research-25D125/` for the committed, hash-verified bundle.
The rest of this section is kept as originally written, below, for the record of what was
and wasn't known at the time; §5 has a full update.

## 3. Why the chip generation has to match the host — the actual mechanism

This is the specific, non-obvious constraint this report is named for. It was discovered empirically, not anticipated:

Apple's `Virtualization.framework` exposes `VZMacOSRestoreImage.mostFeaturefulSupportedConfiguration`, which Apple's own documentation states returns `nil` "if none of the hardware models are supported on the current host." A restore image (IPSW) declares, in its `BuildManifest.plist`, which specific Mac hardware models it supports — and that manifest is generation-specific, not macOS-version-specific.

When this project attempted to create a VM from a real M6-generation IPSW (`UniversalMac_27.2_26B7124_Restore.ipsw`, supporting only `Mac18,1`/`Mac18,2`) on a host whose own chip is an Apple M2 Pro — an *older* generation — the result was immediate and unambiguous:

```
tart create m6-research-vm --from-ipsw=UniversalMac_27.2_26B7124_Restore.ipsw --disk-format asif
Error: UnsupportedRestoreImageError()
```

No partial VM was created; the error fires before any disk allocation. The grounded inference (backed by Apple's documented API behavior, though no exact error-string source was found) is that **Virtualization.framework will not let a host create a VM targeting a newer SoC generation's hardware model than the host's own silicon** — independent of which macOS *version* is involved. A host can virtualize its own chip generation or any older one; it cannot virtualize a chip that doesn't exist yet from its own perspective.

This means the chip-generation relationship between VM and host is not a tuning parameter or a nice-to-have for this research — it is a hard precondition for the VM to exist at all. **"Equal chipset to the host"** (or, more precisely, *at or older than* the host's own chip generation) is the only region of IPSW selection where `tart create --from-ipsw` can succeed on a given machine. Every later step in the four-step evidence chain (§2) is unreachable until this precondition is satisfied, because there is no VM to run `evaluate` against otherwise.

## 4. The practical consequence for this research track

This finding reframes the track's open question (§1 of `progress/goal.md`) rather than closing it:

- The original question — does `bputil`'s SEP/LocalPolicy-dependent mutation path work inside a virtualized guest at all? — is still completely open. It has not been tested, because no VM has yet booted far enough to test it.
- It is specifically *not* answerable using an IPSW for a chip generation newer than the host's own, on this host, under any circumstances — that path fails deterministically at VM creation, before the SEP question is even reachable.
- The chosen way forward (`progress/milestones.md` M8) is to retry VM creation with an IPSW matching a chip generation this exact host can virtualize (`tart create --from-ipsw=latest`, or an exact build match via `sw_vers`), which re-opens the original SEP/LocalPolicy question on hardware that can actually attempt it — without requiring access to different physical hardware and without the physical risk of real scratch-hardware testing.
- This substitution does not change what counts as evidence of an "unlock" (§1–§2 above apply identically regardless of which chip generation the VM targets) — it only changes which IPSW can be used to get a VM booted in the first place. A VM built from an older-or-equal chip generation is not "less of a Mac" for the purposes of this evidence chain; it is simply the only kind of VM this host is capable of creating at all.

## 5. What has — and has not — been evidenced so far

**Updated 2026-11-10, after `evaluate -> plan -> apply -> verify` actually ran.** Original
text below (as of this report's first writing, same day, earlier) is kept for the record;
this list reflects what's true now.

- **Evidenced:** the chip-generation constraint itself (§3), confirmed first-hand against real tooling and grounded in Apple's own documentation.
- **Evidenced:** that a chip-generation mismatch fails deterministically and immediately, with no partial side effects (`tart list` confirmed no VM was created).
- **Evidenced, now:** the full four-step chain in §2, against `vm-sec-research-25D125` (an
  IPSW matching this host's own chip/macOS build) — twice: `Full -> Reduced` and, in a
  second pass, `Reduced -> Full -> Permissive`. Baseline and post-mutation measurements
  were both produced by the real `bputil-eval evaluate`/`verify`/`report` commands (not
  hand-typed `bputil` alone, though that was also used and cross-checked), run on the VM
  itself over SSH. The committed, hash-verified bundle is `evidence/vm-sec-research-25D125/`
  — see its `README.md` for the exact `verify` diff and how to re-check the hashes.
- **Evidenced, now:** `bputil`'s mutation path works inside this VZ guest. This directly
  contradicts the Apple Developer Forums report cited in §1/§3 of
  `plans/research-environment.md` that SEP/LocalPolicy communication fails inside a VZ
  guest — on this host (Apple M2 Pro) and guest macOS build (`26.3`/`25D125`), it does not
  fail. This was the actual open question this whole track existed to answer, and it is
  now answered, affirmatively, with evidence — not assumed and not guessed.
- **Still not evidenced:** any of this through `bputil-eval`'s own `authorize`/`execute`/
  `verify.assert_invariants` pipeline (P3) — every mutating `bputil` command in both passes
  was typed live by the VM's owner (this session's user), per golden rule 4, never
  automated by this project's own tool or by the agent driving the research.

## 6. Summary

"Unlocked," in this project, means one specific, narrow thing: a `SecurityMode` transition away from `Full`, measured fresh by the same owner-authorized, non-bypassing custom toolchain this project builds. Evidencing that inside a disposable VM — rather than on real scratch hardware — turned out to be achievable: the hard precondition this report is named for (VM chip generation cannot exceed the host's own) was satisfiable by building against an IPSW matching the host's own build, and once satisfied, the full `evaluate -> plan -> apply -> verify` chain completed and is now evidenced twice over, up to and including `Permissive` (custom-kernel-capable) mode — see §5 and `evidence/vm-sec-research-25D125/` for the committed proof.
