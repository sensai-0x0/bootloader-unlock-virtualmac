# Goal

**Build a fully simulated macOS research environment — not real owned Apple-Silicon
hardware — and use it to prove, end to end, that bputil-eval can correctly measure a
virtual Mac's boot-chain trust state before and after an owner-authorized security-policy
change, and correctly report when that change has moved the container away from Full
Security.**

Read this before any work in `progress/` or `plans/` that touches the simulated
environment — it's the thing every milestone in `milestones.md` is in service of, and the
thing to re-check against before marking one done.

## What "verifying the virtual OS bootloader is unlocked" means here

This phrase is doing a lot of work and is easy to misread, so pin it down precisely:

- **"Unlocked" has exactly one meaning in this project: `spec/contract-spec.md`'s
  `SecurityMode` moving away from `Full` to `Reduced` or `Permissive`.** It does not mean
  bypassing a signature check, defeating the Secure Enclave, or touching a device or VM
  the person running this project doesn't own or control. `spec/build-spec.md`'s golden
  rules apply here exactly as they do everywhere else in this codebase — a virtual machine
  you created and control is still a device this project only ever modifies through
  Apple's own `bputil`/`kmutil`/`csrutil`, with its own equivalent of an owner present and
  authorizing, never through a bypass.
- **"Verifying" means a fresh measurement, not an assumption.** The success condition for
  every milestone below is `bputil-eval evaluate`/`verify` actually reporting the new
  state, not a plan having been generated or a command having been *attempted*. Golden
  rule 8 (`spec/build-spec.md`: never claim a security state without a fresh measurement
  proving it) applies to this project's own research just as much as it applies to the
  tool it's building.
- **"Simulating the macOS environment" means a VM, built from a real IPSW, that this
  project owns and controls** (see `plans/research-environment.md`'s Track B) — not a
  hand-waved description of what a real Mac would do. If a VM can't actually do the thing
  (see the open question below), that's a finding to record, not a reason to fake the
  result with a hand-built fixture pretending to be a live measurement.

## The open technical question this goal depends on

`plans/research-environment.md` originally surfaced community reports that Apple's
Virtualization.framework may not fully emulate the Secure Enclave / LocalPolicy machinery
`bputil` depends on — one forum report describes `bputil -d` failing inside a VZ guest
with an SEP-communication error ("Failed to create local policy").

**Update, 2026-11-10 (M4 attempted):** that specific question is now moot on the hardware
available to this project, for a more basic reason, confirmed first-hand:
`tart create --from-ipsw=<the real M6 IPSW>` fails outright with
`UnsupportedRestoreImageError()` on this session's host (an Apple M2 Pro). Per Apple's own
`VZMacOSRestoreImage` documentation, the configuration tart needs comes back `nil` when
"none of the hardware models are supported on the current host" — and this IPSW's only
two build identities are both M6-generation. The VM can't even be *created*, let alone
boot far enough to test SEP/`bputil` behavior inside it. See
`plans/research-environment.md`'s "Results from Track B" for the full account.

**This goal still does not assume an answer, it just has a sharper question now.** The
honest end-state so far is "a macOS VM for a chip generation newer than the host's own
can't be built on this hardware at all" — which is a legitimate, useful, *confirmed*
result, not a failure of this research track. Two live paths forward:
1. Retry Track B on a host whose own chip is M6 (or newer) — if one becomes available,
   the original SEP/LocalPolicy question is still open and worth testing then.
2. Treat this as resolved for now and pursue the "unlocked" proof via
   `plans/phase-3.md`'s real-scratch-hardware route instead — which was always the
   fallback this goal anticipated.

Pick one and record the decision in `progress/milestones.md` rather than leaving M5
hanging indefinitely.

**Decision, 2026-11-10:** a third option, safer than either of the two above, found on
reflection: **retry Track B, but with an IPSW for a chip generation this host *can*
virtualize** (`tart create --from-ipsw=latest`, which fetches Apple's own
latest-supported-for-this-host image), instead of either waiting for M6-or-newer hardware
or moving straight to physically risky scratch hardware. This isn't M6-specific anymore —
that's fine, because nothing in "What success looks like" above requires M6 specifically;
the M6 angle was about identity-fixture realism (`plans/research-environment.md` Track A,
already done), not about the mutation proof itself. This option has strictly less risk
than real scratch hardware (fully disposable, no physical device, no DFU-restore
exposure, owner credentials are ones created fresh for this VM) and directly re-opens the
original SEP/LocalPolicy question M5 asked, on hardware that can actually attempt it. See
`progress/milestones.md` for how this goes.

**Resolved, 2026-11-10 (M8/M9/M6):** that question now has a real, measured answer — see
`progress/milestones.md`'s log entries from this date for the full evidence trail.
Against `vm-sec-research-25D125` (built from an IPSW matching this host's own chip/macOS
build, `26.3`/`25D125`), **SEP/LocalPolicy communication works inside this VZ guest**: the
Apple Developer Forums "Failed to create local policy" failure did not reproduce.
`bputil -d` returned a real, paired local policy both before and after a live,
human-typed `bputil -g -k -v <vuid>` run from the VM's recovery (1TR-equivalent)
environment, and a fresh post-reboot measurement showed `Security Mode: Reduced` and
`3rd Party Kexts Status: Enabled` as genuinely new, signed manifest values (changed nonce
hash, incremented Cryptex generation) — not an assumption, not a cached read. This
satisfies every item in "What success looks like" below against a VM, closing the open
question this goal has carried since M4/M5 without needing M6-or-newer hardware or real
scratch hardware.

## How this relates to the rest of the project

- `plans/phase-0.md` through `phase-2.md` (read-only evaluator and planner) are
  prerequisites that are already done — this goal doesn't re-litigate them.
- `plans/phase-3.md` and `phase-4.md` (the real `authorize`/`execute`/`verify` mutation
  pipeline) are also prerequisites: nothing in this goal can "verify an unlock" without
  that pipeline existing and being exercised against *something* — real scratch hardware
  or a VM, whichever turns out to work. Building that pipeline isn't optional busywork
  blocking this goal; it's the same code either way.
- `plans/research-environment.md` is the research record this goal continues from —
  read "Results from the real IPSW" there before starting `milestones.md`'s VM-boot
  milestone.

## What success looks like, concretely

A session transcript (or evidence bundle, per `spec/contract-spec.md`'s
`EvidenceComplete`) showing, against a VM this project built and controls:
1. `evaluate` reporting `security_mode: Full` as the baseline.
2. `plan` producing a transition to a target profile.
3. The VM's own equivalent of 1TR, with its own owner-present authorization, actually
   running `apply`.
4. `evaluate`/`verify` run again, reporting the new, non-`Full` `security_mode` — a fresh
   measurement, not an inference.

If step 3 turns out to be technically impossible inside a VM (see the open question
above), success instead looks like: a clearly written, evidenced finding to that effect in
`milestones.md`, plus an explicit decision about whether to pursue the same proof on real
scratch hardware per `plans/phase-3.md` instead.
