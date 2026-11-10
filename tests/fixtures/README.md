# Fixtures

Captured real output from Apple's own tools, per `spec/phased-plan.md`'s P0 "Fixtures
harness" workstream ("Capture real `bputil -d`, `csrutil status`, `nvram -p` and `ioreg`
output into `tests/fixtures` for deterministic parser tests").

## Provenance

| File | Captured via | Chip | macOS build |
|---|---|---|---|
| `bputil_help_v0.1.14.txt` | `bputil -h` | Apple M2 Pro | 25D125 |
| `csrutil_status.txt` | `csrutil status` | Apple M2 Pro | 25D125 |
| `csrutil_authenticated_root_status.txt` | `csrutil authenticated-root status` | Apple M2 Pro | 25D125 |
| `sw_vers_buildVersion.txt` | `sw_vers -buildVersion` | Apple M2 Pro | 25D125 |
| `sysctl_machdep_cpu_brand_string.txt` | `sysctl -n machdep.cpu.brand_string` | Apple M2 Pro | 25D125 |
| `diskutil_info_root_REDACTED.txt` | `diskutil info /` | Apple M2 Pro | 25D125 |
| `system_profiler_hardware_REDACTED.txt` | `system_profiler SPHardwareDataType` | Apple M2 Pro | 25D125 |
| `ioreg_platform_expert_device_REDACTED.txt` | `ioreg -rd1 -c IOPlatformExpertDevice` | Apple M2 Pro | 25D125 |
| `image4_apticket.der` | vendored, not captured — see below | n/a | n/a |
| `diskutil_apfs_listVolumeGroups_REDACTED.txt` | `diskutil apfs listVolumeGroups` | Apple M2 Pro | 25D125 |
| `diskutil_apfs_listVolumeGroups_SYNTHETIC_multi.txt` | hand-built, not captured — see below | n/a | n/a |
| `sysctl_machdep_cpu_brand_string_M6.txt` | real IPSW's device tree `SoC Name` field, not `sysctl` — see "`_FIRMWARE_TEMPLATE` fixtures" below | Apple M6 (`Mac18,1`) | 26B7124 |
| `sw_vers_buildVersion_M6.txt` | real IPSW's `BuildManifest.plist` `ProductBuildVersion` | Apple M6 (`Mac18,1`) | 26B7124 |
| `system_profiler_hardware_M6_FIRMWARE_TEMPLATE.txt` | assembled from real IPSW data — see below | Apple M6 (`Mac18,1`) | 26B7124 |
| `ioreg_platform_expert_device_M6_FIRMWARE_TEMPLATE.txt` | real IPSW's device tree, converted to ioreg's text shape — see below | Apple M6 (`Mac18,1`) | 26B7124 |

`image4_apticket.der` is a real, signed IM4M manifest, copied verbatim from the `image4`
crate's own test suite (`tests/data/apticket.der` in `image4` v0.8.2, `MIT OR Apache-2.0`
licensed) rather than captured from a device. It's used by `src/state/img4.rs`'s
`parses_a_real_signed_manifest` test to prove the parser against real DER structure without
needing to extract a manifest from a multi-GB IPSW. It is binary, not text, and is not
redacted — it was never tied to a real device in the first place (it's the crate authors'
own synthetic test fixture).

`diskutil_apfs_listVolumeGroups_SYNTHETIC_multi.txt` is hand-built, not captured: this
development machine only has one real APFS volume group, so there was nothing real to
capture for the "exclude the target, keep the others" branch of
`src/state/collect.rs`'s `extract_other_containers`. It's structured to match the real
single-group capture's format with a second, fabricated group added. If a machine with a
genuine second bootable volume group becomes available, replace this with a real redacted
capture and update `src/state/collect.rs`'s corresponding test.

All of the remaining text fixtures above were captured from macOS (not 1TR) — these are the commands `env`/`state/collect`
can run without elevation. All are read-only and change nothing on the host they were captured
from (golden rule 3).

## `_FIRMWARE_TEMPLATE` fixtures

A third label, alongside `_REDACTED` (a real device capture with PII removed) and
`_SYNTHETIC` (hand-built, no real source at all): `_FIRMWARE_TEMPLATE` means the values are
real, but extracted from Apple's own unpersonalized firmware — not run on, or captured
from, a live booted device, because no such M6 device was available (see
`plans/research-environment.md` for the full research). Concretely, these four were built
from `UniversalMac_27.2_26B7124_Restore.ipsw`'s `BuildManifest.plist` and device tree
(`ipsw plist`, `ipsw dtree --json`, both from `blacktop/ipsw`):

- `sysctl_machdep_cpu_brand_string_M6.txt` and `sw_vers_buildVersion_M6.txt` carry **no**
  `_FIRMWARE_TEMPLATE` suffix even though they came from the same research, because their
  values are exact, unambiguous facts (the device tree's `SoC Name` is literally what
  `sysctl -n machdep.cpu.brand_string` reports on real hardware of that generation; the
  build version is literally `BuildManifest.plist`'s `ProductBuildVersion`) — there's
  nothing templated or placeholder about them.
- `system_profiler_hardware_M6_FIRMWARE_TEMPLATE.txt` and
  `ioreg_platform_expert_device_M6_FIRMWARE_TEMPLATE.txt` **do** carry the suffix: their
  identity-shaped fields (serial, model/config/region numbers) are Apple's own generic
  `syscfg/...,zeroes/...` placeholders from the firmware template, not real per-device
  values — there is no real M6 serial number to redact, because no real M6 device backed
  this. The `system_profiler` fixture is deliberately partial (only `Model Name`, `Model
  Identifier`, `Chip`, and a placeholder serial line) rather than guessing fields this
  research didn't actually confirm (firmware version, core count, memory size, etc.) — see
  `plans/research-environment.md`'s "Results from the real IPSW" section for exactly what
  was and wasn't confirmed.

## What's missing

`bputil -d` (and `-d -j`), i.e. the actual local-policy display, **requires root**
(confirmed on this machine: without `sudo`, it fails with "The tool requires running as
root"). Capturing it means running `sudo bputil -d` interactively and pasting the real
output — something this agent cannot do itself, since typing the sudo password is a human
action, and the tool must never automate, store, or prompt for that credential
(`spec/build-spec.md` golden rule 4; `state/collect.rs`'s module doc explains why it uses
`sudo -n` and degrades to `SecurityMode::Unknown` rather than ever touching that prompt).
**A maintainer with physical access should capture this once**, per macOS build and chip
generation in the hardware matrix (`spec/phased-plan.md`'s P5 "Coverage across the hardware
matrix"), and add it here — redacted the same way the files below are.

Per-chip-generation coverage (per `spec/phased-plan.md`'s hardware test matrix) is a P5
concern; this repo has real-hardware fixtures from the one Apple Silicon Mac available
during initial development (M2 Pro), plus `_FIRMWARE_TEMPLATE` identity fixtures for M6
derived from a real IPSW rather than real hardware (see above) — genuine M6 hardware
fixtures, especially a real `bputil -d` capture, are still an open item.

## Why `system_profiler`, not `ioreg`, for the serial number

`ioreg_platform_expert_device_REDACTED.txt` is kept for reference, but `state/collect.rs`
reads the serial from `system_profiler SPHardwareDataType` instead. Confirmed on real
hardware: running the same `ioreg -rd1 -c IOPlatformExpertDevice` invocation twice, a few
seconds apart, produces different output even with nothing about the device's security
state having changed — the top-level object line carries a live uptime counter (`busy N ms`)
that free-runs. `diskutil info /` has the same problem (`Container Free Space` /
`Volume Used Space` change as the filesystem is written to in the background).
`system_profiler SPHardwareDataType`, by contrast, reports static hardware facts and was
confirmed byte-identical across two calls. See `state/collect.rs`'s module doc for how this
shaped what goes into `evidence.raw_outputs`.

## Redaction

`diskutil_info_root_REDACTED.txt` and `ioreg_platform_expert_device_REDACTED.txt` have every
UUID-shaped value and both serial-number fields (`IOPlatformSerialNumber`, `serial-number`,
`mlb-serial-number`) replaced with placeholders before being committed. These are real,
device-identifying values from the capturing machine and `contract-spec.md`'s own
`host.serial_masked` constraint ("at most the last 4 characters; never the full serial")
exists precisely because this tool must not leak them — that constraint should extend to the
fixtures that test it. **Never commit an unredacted capture.** If you add a fixture, redact
serials and volume/platform UUIDs the same way (a trivial `sed` pass; see the capture history
for this directory for the exact substitutions used).
