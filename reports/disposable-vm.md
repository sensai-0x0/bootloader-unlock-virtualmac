# Disposable VM Research Track Report

**Report date:** 2026-11-10
**Source material:** `progress/goal.md`, `progress/milestones.md`, `plans/research-environment.md`
**Status:** In progress (M8/M9 not yet complete)

## 1. What this track is and is not

This is a research track running alongside the phased build plan, not part of the shipped tool itself. Its goal, stated precisely in `progress/goal.md`, is:

> Build a fully simulated macOS research environment — not real owned Apple-Silicon hardware — and use it to prove, end to end, that `bputil-eval` can correctly measure a virtual Mac's boot-chain trust state before and after an owner-authorized security-policy change, and correctly report when that change has moved the container away from Full Security.

It exists because `spec/phased-plan.md`'s P3 exit gate (`reports/execution-product.md` §6) requires a disposable scratch target, and real scratch hardware carries physical risk (DFU-restore exposure, a real device at stake). A disposable VM — fully virtual, no physical device, owner credentials created fresh for the VM — is strictly lower-risk if it can do the same job.

**This track never attempts to bypass a signature check, defeat the Secure Enclave, or touch a device this project doesn't own or control.** A VM created by this project is still a device that is only ever modified through this project's custom toolchain driving `bputil`/`kmutil`/`csrutil`, with its own equivalent of an owner present and authorizing — exactly as `spec/build-spec.md`'s golden rules require for real hardware.

## 2. Two tracks, honestly labeled separately

`plans/research-environment.md` splits the work in two, because each produces a different, non-interchangeable kind of evidence:

### Track A — static ground truth from the IPSW (no execution, no risk)

Reads files out of a real macOS restore image (`UniversalMac_27.2_26B7124_Restore.ipsw`, 20.8 GB) using [`blacktop/ipsw`](https://github.com/blacktop/ipsw). Nothing runs on a device; nothing talks to Apple's servers; nothing mutates anything.

**Completed and confirmed, 2026-11-10:**
- The IPSW supports exactly two devices, both plain M6 (`t8152`, ARMv9.5-A, no Pro/Max tier): `Mac18,1` (MacBook Pro 14", board `J804AP`) and `Mac18,2` (iMac 24", board `J833ctAP`).
- `BuildManifest.plist` confirms `ProductVersion: 27.2`, `ProductBuildVersion: 26B7124`.
- Device-tree extraction (`ipsw dtree --filter j804ap`) confirms the real `SoC Name: Apple M6 (t8152)` string, upgrading a fixture that had been labeled merely "pattern-inferred" to a confirmed value.
- A real `iBoot.j804.RELEASE.im4p` was fed into this project's own `state::img4::parse_manifest_der` as a one-off check: it correctly rejected the input (`Err(Decode(...))`, IM4P vs. the expected IM4M schema) rather than silently misparsing it — the fail-closed behavior `spec/build-spec.md` requires, confirmed against a real unexpected input type.
- Four fixtures were built from these real, firmware-sourced values under `tests/fixtures/`, following the project's existing `_REDACTED`/`_SYNTHETIC`/`_FIRMWARE_TEMPLATE` labeling convention (see `tests/fixtures/README.md`).

### Track B — a real macOS VM, for OS-version tool *behavior* only

Scoped narrowly, by design: to observe how `bputil --help`, `csrutil status` wording, etc. actually look on the real macOS build a given chip generation ships — never to obtain that generation's real identity strings (Track A already does that, more reliably) and never to assert a real security state without a fresh measurement proving it.

Tooling: [`tart`](https://github.com/cirruslabs/tart), confirmed to build a macOS VM directly from a local IPSW with no Xcode/Swift Virtualization.framework code required.

## 3. What has actually been attempted, and what blocked it

### Attempt 1 — M6 IPSW on an M2 Pro host (blocked at VM creation)

```
tart create m6-research-vm --from-ipsw=UniversalMac_27.2_26B7124_Restore.ipsw --disk-format asif
Error: UnsupportedRestoreImageError()
```

No partial VM was created. Root cause, grounded in Apple's own documentation (not guessed): `VZMacOSRestoreImage.mostFeaturefulSupportedConfiguration` is `nil` "if none of the hardware models are supported on the current host." This IPSW's only build identities are M6-generation; the host in this session is an Apple M2 Pro — an *older* chip generation than the image targets. The strong, documentation-backed inference is that Virtualization.framework will not create a VM targeting a newer SoC generation than the host's own silicon, independent of macOS version.

This is a different, earlier blocker than the one originally anticipated (community reports that SEP/LocalPolicy communication fails *inside* a VZ guest, which would have blocked the mutation proof after a successful boot). That original question is now moot on this host, for a more basic reason: the VM cannot be created at all.

### Decision — a third, safer option

Rather than wait for access to an M6-or-newer host, or pivot straight to real scratch hardware (physically riskier), the chosen path is to retry Track B with an IPSW for a chip generation **this host can actually virtualize** — i.e., matching or older than the host's own chip generation. This re-opens the original SEP/LocalPolicy question on hardware that can actually attempt it, while remaining fully disposable: no physical device, no DFU-restore exposure, no real credentials at stake. See `reports/unlocked-bootloader-evidence.md` for why this chipset-generation constraint is the load-bearing fact for the whole research track, not an incidental detail.

### Attempt 2 — `tart create --from-ipsw=latest` (failed twice, network)

`--from-ipsw=latest` resolved to `UniversalMac_26.6.2_25G83`. Both attempts failed mid-download with `Error: The network connection was lost.` (at 41% and 70% respectively). `tart` does not resume a dropped download — each retry restarted from zero bytes — and does not clean up a stale partial on failure; an 18 GB partial file was left in `~/.tart/cache/IPSWs/` and manually removed, with the user's confirmation, per this repository's host-impact policy.

A separate, independent failure also surfaced once: `Error: A software update is required to complete the installation.` — a known `VZErrorDomain` pattern when the host is missing newer device-support files a given guest image needs, consistent with this host's Xcode (26.6) being behind the then-current 27.0. Updating Xcode was rejected as the fix (a real, unconfirmed host-level change); instead the plan shifted to targeting the *exact* IPSW build this host is already running (`UniversalMac_26.3_25D125`, confirmed via `sw_vers` to match this host precisely), found via a read-only `ipsw download ipsw --macos --version 26.3 --urls` lookup.

### Attempt 3 — exact-match IPSW download (downloader-specific failures, resolved)

The exact-match download also hit `The network connection was lost` via `tart`'s own downloader, and separately failed differently via `ipsw download ipsw`'s own downloader ("initial request... failed," no detail, at the first byte) — while a plain `curl -I` against the identical URL succeeded immediately. This isolated the failure to both tools' downloader implementations specifically, not the network or the URL itself. The current approach is a direct `curl -C - --retry 5 --retry-delay 5` download (resume-capable, auto-retrying), reported in progress as of the last milestones log entry, not yet confirmed complete.

## 4. Host-impact disclosure

Per this repository's `CLAUDE.md`, the following host-level changes were made in service of this research track and are flagged here for the user's awareness and disposition, as that file requires:

- `blacktop/ipsw` installed via Homebrew.
- `tart` v2.41.1 installed — not via its (broken) Homebrew formula, but by downloading the binary release directly from `cirruslabs/tart`'s GitHub releases and keeping it as an intact `.app` bundle (copying the raw Mach-O out trips Gatekeeper/AMFI).
- Two macOS restore images downloaded to local disk: the real M6 image (~20.8 GB, gitignored, in the repo root) and an in-progress `26.3` image (partial, via `curl`, location per the `tart`/`curl` commands above).
- One 18 GB stale partial download in `~/.tart/cache/IPSWs/` was removed, with the user's confirmation at the time.

**None of this has been confirmed cleaned up as of this report.** If this track is picked back up, or concluded, the open question from `CLAUDE.md` still stands: whether to keep or remove `blacktop/ipsw`, `tart` and its `.app` bundle, and the cached/downloaded restore images.

## 5. Current status

| Milestone | Status |
|---|---|
| M0–M2 (plan written, Track A run, M6 fixtures committed) | Done |
| M3 (mutation pipeline implemented and proven on *some* target) | Not started |
| M4 (VM built from the real M6 IPSW) | Blocked — `UnsupportedRestoreImageError()` |
| M5 (whether `bputil`'s mutation path works inside that VM) | Moot on this host — superseded by M4's earlier block |
| M6 (end-to-end evaluate→plan→apply→verify inside the VM) | Not started; blocked on M3–M5 |
| M7 (written finding + decision on the VM-vs-real-hardware fork) | Decided — see §3's "third, safer option" |
| M8 (VM built from a chip generation this host can virtualize) | In progress — download/creation attempts ongoing, not yet confirmed to succeed |
| M9 (whether `bputil`'s mutation path works inside *this* VM) | Not started; blocked on M8 |

## 6. Summary

The disposable-VM track is a legitimate, carefully scoped attempt to find a lower-risk substitute for real scratch hardware when proving the mutation half of `bputil-eval`. It has produced solid, confirmed static ground truth (Track A) and one clear, documented, non-obvious finding (Track B's chip-generation blocker). It has not yet produced a booted VM, let alone any evidence about whether `bputil`'s SEP-dependent mutation path actually works inside one — that remains the open question this entire track exists to answer, and `reports/unlocked-bootloader-evidence.md` covers exactly what evidence would be required to answer it honestly.
