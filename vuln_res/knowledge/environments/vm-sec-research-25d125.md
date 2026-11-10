---
id: vm-sec-research-25d125
provider: tart
lifecycle: disposable
status: active
created_at: 2026-11-10T23:00:00Z
created_by: human (this session's user), with the coordinating session driving `tart`
approved_for: [security-mode-measurement-research, bputil-eval-live-tool-verification]
approved_by: human
network: host-bridged (tart's default shared/NAT networking; reachable at 192.168.64.4 at
  time of writing — a VM's DHCP-assigned address, not guaranteed stable across reboots)
resource_caps: { cpu: "default tart allocation", mem: "default tart allocation", time_budget: "no fixed budget — long-lived across this project's M8-M10 research and multiple vuln_res sweeps" }
---

Not created by `vulnres-environment-runner` or any `vuln_res/` agent — predates the
current agent suite, created directly by the coordinating session and the user together
(`progress/milestones.md`'s M8 entry) for the root project's own research goal (proving
`bputil-eval` correctly measures a real `SecurityMode` transition), not originally a
vuln_res-suite environment at all. Registered here retroactively so this suite's own
registry isn't blind to an environment that already exists and that vuln_res work has
since used (this session's research into the `env-1tr-fallback-detection-confirmed-broken`
finding read from it, read-only, via the fixtures it already produced — no new execution
performed against it in that pass).

**What it is:** a `tart` VM built from an IPSW matching this host's own chip/macOS build
(`26.3`/`25D125`), so it can actually boot (a newer-chip-generation IPSW fails outright —
see `plans/research-environment.md`). Local account `test`, Remote Login enabled.

**What's been run inside it:** the full `evaluate -> plan -> apply -> verify` round trip
(`Full -> Reduced -> Full -> Permissive`), both via raw `bputil`/`csrutil` and via the real
`bputil-eval` binary copied over and run live (`progress/milestones.md` M9/M10). Produced
the `tests/fixtures/bputil_d_*_VM_VIRTUALIZED.txt` fixtures and the evidence bundle under
`evidence/vm-sec-research-25D125/`.

**Known limitation, confirmed via this session's research
(`../fallback-recoveryos-is-likely-real-hardware-only.md`):** this VM's `--recovery` boot
only ever produces the paired/1TR recovery environment — there's no confirmed way to make
it (or any `tart`/Virtualization.framework VM) produce genuine fallback/"ordinary"
recoveryOS, which appears to require a second physical APFS container and a Boot-ROM-level
gesture no VM API exposes. Don't re-attempt that specific experiment against this
environment without new information changing that assessment.

**Last known state:** left running, in `Permissive` security mode, after the M10 round
trip. Not torn down — still useful as a live target for further `bputil-eval` verification
work. Owner credentials were created fresh for this VM and are not recorded here (same
`NoCredentialHandling` spirit as everywhere else in this project).
