# 🐜 the-ant-experiment

A custom toolchain that **measures and changes an Apple Silicon Mac's boot-security mode** — safely, honestly, and only through Apple's own gates. 🕵️ An OS Vulnerability Researcher agent suite (`vuln_res/`) rides alongside it, hunting bugs in this toolchain's own code — never in Apple's platform.

## 🎯 The goal

Apple Silicon Macs ship in `Full` security mode. Two looser modes exist, reached only by the device's own owner, physically present in **1TR** (One True Recovery), typing their own credentials:

| Mode | Unlocks |
|---|---|
| 🔒 `Full` | default, no special access |
| 🔓 `Reduced` | third-party kernel extensions |
| 🔧 `Permissive` | a fully custom/unsigned kernel |

**"Unlocking the bootloader," here, means exactly one thing: proving — with a fresh measurement, not an assumption — that `SecurityMode` moved off `Full`.** No signature bypass. No Secure Enclave trickery. Every mutation goes through `bputil` / `kmutil` / `csrutil`, driven by this toolchain (`bputil-eval`), with a human owner in the loop every time.

## ✅ Success, evidenced

On 2026-11-10, the full chain ran end-to-end against a disposable VM this project built and controlled:

```
evaluate → Full          🔒 baseline, freshly measured
plan      → Reduced       📝 transition planned
apply     → Reduced       🔓 owner-authorized, live in 1TR
verify    → Reduced       ✅ fresh measurement confirms it
  ...then further...
revert    → Full          🔒 round-trip proven
apply     → Permissive    🔧 custom-kernel mode reached
verify    → Permissive    ✅ fresh measurement confirms it
```

The `verify` diff, produced by the real binary, not hand-typed:

```
security_mode:        Reduced → Permissive
ssv_enabled:           true → false
allows_custom_kernel:  false → true
```

Hash-verified, committed evidence bundle → [`evidence/vm-sec-research-25D125/`](evidence/vm-sec-research-25D125/README.md)
Full research narrative → [`progress/milestones.md`](progress/milestones.md) · [`progress/goal.md`](progress/goal.md)

## 🧭 Where it stands

- **Read-only tooling (evaluate/plan/report):** done ✅
- **Proof the whole chain works on real boot-security hardware (via a VM):** done ✅
- **The mutation pipeline built into `bputil-eval` itself (`authorize`/`execute`):** not started — every mutation above was typed live by a human owner, on purpose, per project rule.

No install, no exploit, no bypass — just a toolchain that tells the truth about what state your Mac is actually in. 🐜
