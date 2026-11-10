# Research environment — simulating an M6-generation Mac from an IPSW

Track A below has now actually been run, against the real file
`UniversalMac_27.2_26B7124_Restore.ipsw` (20.8 GB) in this repo's root — see "Results from
the real IPSW" at the end of this file for what came back. The rest of this document is
the plan as originally written (kept intact rather than rewritten after the fact, so you
can see what was predicted vs. confirmed); Track B (the VM) has not been run.

## 0. First finding: check what your IPSW actually is before anything else

"M6 Pro" is worth pinning down precisely, because public reporting as of this research
says it may not exist as a distinct chip:

- Apple announced a 14-inch **MacBook Pro with the plain M6 chip** on 27 October 2026
  (on sale 6 November 2026) — not an "M6 Pro" silicon tier. Pre-launch reporting
  specifically said Apple is *not* making M6 Pro/Max variants this cycle, and is holding
  the Pro/Max tier back for the M7 generation in 2027.
- TheAppleWiki identifies that machine as **`Mac18,1`**, board **`J804AP`**, model
  **`A3536`**.
- No M6 Pro/Max board ID or chip ID turned up in this research anywhere public.
- **Confirmed directly from the real IPSW** (not secondhand reporting): it supports
  exactly two devices, both plain M6, no Pro/Max — see the results section. The "M6 Pro"
  naming concern in this section was correct.

So "Mac M6 Pro" most likely means **"the M6-chip MacBook Pro" (`Mac18,1`)** — i.e. the
*laptop line* is "Pro," not the *chip tier*. But don't take my word for it: **your IPSW's
`BuildManifest.plist` is the actual ground truth.** Confirm before building anything else:

```bash
brew install blacktop/tap/ipsw   # if not already installed
ipsw info -j -l /path/to/your.ipsw          # top-level metadata + file listing
unzip -p /path/to/your.ipsw BuildManifest.plist > /tmp/BuildManifest.plist
ipsw plist /tmp/BuildManifest.plist --no-color | jq '.SupportedProductTypes, .ProductVersion, .ProductBuildVersion'
```

If `SupportedProductTypes` contains something other than `Mac18,1`, or if there's a chip
ID/board ID you don't recognise, stop and re-derive the rest of this plan from what the
manifest actually says rather than from this document's assumption.

## 1. What you can and can't realistically simulate

Grounded in how Apple's restore/personalization pipeline actually works (per
`theapplewiki.com`, the `img4tool` README, and `idevicerestore`'s source, all checked
during this research):

- An IPSW contains **generic, unpersonalized firmware payloads** (`IM4P` containers: iBoot,
  LLB, SEP firmware, kernelcache, etc.) plus `BuildManifest.plist`, which lists each
  component's expected hash and which device/board IDs it's valid for. It does **not**
  contain a signed `IM4M` boot ticket for any specific device — that's issued by Apple's
  TSS ("Tatsu") server per-ECID, over the network, at actual restore time.
- That means **this research cannot produce a real, Apple-signed manifest for a device
  that doesn't exist on your desk** — and per `spec/build-spec.md`'s golden rules, this
  project doesn't attempt to forge one or talk to TSS on anyone's behalf anyway. Nothing
  below tries to.
- A macOS VM built from this IPSW (see §3) gets a **virtualized, generic hardware
  identity** (community reports show identifiers like `VirtualMac2,1`), not `Mac18,1`. It
  will run the *real macOS build* M6 ships with, with *real* `csrutil`/`sw_vers`/`bputil
  --help` output for that OS version — but its chip/board/model strings won't be M6's, and
  its SEP/LocalPolicy behavior is reported unreliable in VMs (one forum report: `bputil -d`
  inside a VZ guest fails with an SEP-communication error, "Failed to create local
  policy"). **Never treat a VM's security-mode output as representing real M6 hardware.**

Given that, the realistic design is two tracks that each produce a different, honestly
labeled kind of fixture — not one track pretending to be both.

## 2. Track A — static ground truth from the IPSW (no execution, no risk)

Everything here just reads files out of the IPSW. Nothing runs on a device, nothing talks
to Apple's servers, nothing mutates anything — nothing to clear with the golden rules
beyond what P0's fixtures harness already established.

Tooling: [`blacktop/ipsw`](https://github.com/blacktop/ipsw) (`brew install
blacktop/tap/ipsw`) — a widely used, open-source iOS/macOS firmware research CLI, already
confirmed to have the subcommands below (checked against its live docs during this
research, not guessed).

```bash
# 1. Top-level info and file listing
ipsw info -j -l your.ipsw > research/ipsw_info.json

# 2. BuildManifest.plist -> JSON (chip/board IDs, supported products, OS version)
unzip -p your.ipsw BuildManifest.plist > research/BuildManifest.plist
ipsw plist research/BuildManifest.plist --no-color | jq . > research/BuildManifest.json

# 3. Cross-reference against Apple's device database (confirms board/chip ID independently
#    of whatever BuildManifest says, and independently of this document's Mac18,1 guess)
ipsw device-info --prod Mac18,1 --json > research/device_info.json
#    (swap Mac18,1 for whatever step 0 actually found)

# 4. Device tree — gives you the real "compatible"/model/manufacturer strings an M6 Mac's
#    ioreg/system_profiler would show (same data shape as
#    tests/fixtures/ioreg_platform_expert_device_REDACTED.txt and
#    tests/fixtures/system_profiler_hardware_REDACTED.txt, but from real M6 firmware)
ipsw extract --dtree --output research/ your.ipsw

# 5. Kernelcache (not needed for P0-P2's parsers, but useful now while you're at it, for
#    phase-5.md's eventual per-generation fuzzing corpus)
ipsw extract --kernel --output research/ your.ipsw
```

For IM4P-level inspection (confirm exact flags with `ipsw img4 im4p --help` and `ipsw img4
im4m --help` locally before relying on this — the live docs site didn't give me every
subcommand's flags, only the subcommand names: `img4 extract`, `img4 im4p`, `img4 im4m`,
`img4 im4r`, `img4 info`, `img4 kbag`). `img4 im4m`'s own subcommands are `extract` (from an
SHSH blob — you don't have one, so skip this), `info`, and `verify` (against a
BuildManifest — useful to confirm a component's digest matches what's expected, not to
obtain a signature).

**What this track gives you, concretely:** real chip ID, board ID, model identifier,
`ProductVersion`/`ProductBuildVersion` (the macOS version M6 ships with), and real device
tree strings — everything `env::host()` and `state/collect.rs`'s serial/volume-group
parsers care about on the identity side, grounded in the actual firmware rather than
guessed.

## 3. Track B — a real macOS VM, for OS-version tool *behavior* only

**Attempted and blocked — see "Results," below, for the confirmed reason before trying
this again.** Originally scoped narrowly: use this only to see how `bputil --help`,
`csrutil status` wording, etc. look on the *actual macOS build* M6 ships with — not to get
M6's identity strings (see §1) and not to assert any real security state.

Tooling: [`tart`](https://github.com/cirruslabs/tart) (the Homebrew formula
`cirruslabs/cli/tart` was broken against this Homebrew version at the time this was run —
see "Results" — the release tarball from GitHub worked once extracted and kept as an
intact `.app` bundle rather than copying out the raw binary, which trips Gatekeeper/AMFI)
— confirmed to support building a macOS VM directly from a local IPSW file, no
Xcode/Swift Virtualization.framework code needed:

```bash
tart create --from-ipsw=/path/to/your.ipsw m6-research-vm
tart run m6-research-vm
# then, inside the guest (via screen sharing or tart's own display):
sw_vers -buildVersion
bputil -h
csrutil status
sysctl -n machdep.cpu.brand_string   # expect a virtualized/generic value, NOT "Apple M6" —
                                      # this confirms the §1 limitation rather than refuting it
```

If you'd rather copy the actual `bputil-eval` binary into the guest and run `evaluate
--json` against it, that's a reasonable use of this track too — it'll exercise the real
parsers against a real (if virtualized) `bputil -d`/`csrutil status`, which is strictly
more real than anything hand-written. Just don't commit its `security_mode` output as a
fixture claiming to represent M6 hardware; label it `_VM_VIRTUALIZED` if you keep it at
all, the same way existing fixtures are labeled `_REDACTED` or `_SYNTHETIC`.

## 4. Assembling fixtures, and how to label them honestly

Once Track A (and optionally B) have run, build new fixtures under `tests/fixtures/`
following the existing project convention exactly — see `tests/fixtures/README.md`'s
provenance table and its `_REDACTED`/`_SYNTHETIC` naming precedent
(`diskutil_apfs_listVolumeGroups_SYNTHETIC_multi.txt` is the closest existing example of
"hand-assembled, not captured, and the filename says so").

| What | Source | How to label it |
|---|---|---|
| `host.chip` string (e.g. `"Apple M6"`) | **Pattern-inferred**, not measured: every M1–M5 generation reports `sysctl -n machdep.cpu.brand_string` as `"Apple M<N>[ Pro/Max/Ultra]"`. Nothing in Track A or B actually produces this string for hardware that doesn't exist. | `sysctl_machdep_cpu_brand_string_M6_PATTERN_INFERRED.txt`, with a comment in `tests/fixtures/README.md` saying exactly that |
| `host.macos_build` | Real — `BuildManifest.plist`'s `ProductBuildVersion` (Track A, step 2) | No special label needed; it's a real, if unpersonalized, firmware fact |
| Device tree / `ioreg`-shaped identity strings | Real — Track A step 4 | `ioreg_platform_expert_device_M6_REDACTED.txt` (still redact anything serial-shaped, same as the existing fixtures, even though this is firmware data not a live device — be consistent) |
| `bputil -h` / `csrutil status` wording for that OS version | Real, if you ran Track B | `bputil_help_M6_VM_VIRTUALIZED.txt` |
| `bputil -d` / actual `security_mode` | **Not obtainable** by this plan at all (§1) — do not fabricate one | Don't create this fixture. Leave it as an open item, same as `tests/fixtures/README.md`'s existing "What's missing" section, until real M6 hardware is available for `phase-0.md` item 2's process |

## 5. How this maps to the existing phases and golden rules

- This is prep work for `phase-5.md`'s "hardware matrix coverage" item 1 — a way to get
  identity-level fixture coverage for a chip generation before owning the hardware, which
  that file didn't previously account for (it assumed physical access to each generation).
  Update `phase-5.md` to reference this file once fixtures land.
- Nothing here crosses any golden rule in `spec/build-spec.md`: no personalization, no
  signing, no claim of a verified security state without a real measurement (§1 and §4 are
  explicit about this), no mutation, no device ownership claimed over hardware that isn't
  owned (there's no device here at all — it's firmware analysis).
- Track B's VM is not a "scratch container" in `phase-3.md`/`phase-4.md`'s sense — it
  can't exercise `bputil`'s real mutation path (SEP communication reportedly fails in VZ
  guests) or an owner-present 1TR flow, so it doesn't shortcut P3/P4's hardware
  requirement. Don't treat a successful VM boot as license to start P3 without real
  hardware.

## Results from the real IPSW

Ran against `UniversalMac_27.2_26B7124_Restore.ipsw` on 2026-11-10. Tool:
`blacktop/ipsw` v3.1.743 (installed via `brew install blacktop/tap/ipsw` for this). Every
value below is read directly out of the file — none of it is this document's earlier
guesses, though in every case where this doc had guessed, the file confirmed it.

**`ipsw info -j`:**
```json
{"type":"IPSW","version":"27.2","build":"26B7124","os":"Production","devices":[
  {"name":"MacBook Pro (14-inch, M6)","product":"Mac18,1","board":"J804AP",
   "cpu":"CPU: M6 (ARMv9.5-A), ID: t8152"},
  {"name":"iMac (24-inch, M6)","product":"Mac18,2","board":"J833ctAP",
   "cpu":"CPU: M6 (ARMv9.5-A), ID: t8152"}
]}
```

- **§0's naming concern was correct, confirmed first-hand, not just from secondary
  reporting.** This Universal Mac restore image supports exactly two devices, both the
  plain M6 chip (`t8152`, `ARMv9.5-A`) — no Pro/Max tier. The OS itself is already at
  **macOS 27.2** (not "Tahoe 26.x" as this document's earlier research round assumed —
  that research was working from cached/pre-release-era pages; the real file is the
  authoritative source here, exactly per §0's own advice to check it rather than trust
  secondhand naming).
- `BuildManifest.plist` (extracted via `unzip -p ... BuildManifest.plist`, converted via
  `ipsw plist ... | jq`) confirms `ProductVersion: 27.2`, `ProductBuildVersion: 26B7124`,
  `SupportedProductTypes: ["Mac18,1", "Mac18,2"]`, `DeviceClass` lowercase (`j804ap`,
  `j833ctap` — same boards, TheAppleWiki's casing was just cosmetically different), and
  firmware paths like `Firmware/all_flash/iBoot.j804.RELEASE.im4p` and
  `kernelcache.release.mac18g`.
- `ipsw dtree --filter j804ap --summary` against the IPSW directly (no need to manually
  extract+decode the IM4P first — the subcommand handles that) gives:
  ```
  Model: Mac18,1   Board Config: J804AP   Product Name: MacBook Pro (14-inch, M6)
  SoC Name: Apple M6 (t8152)
  ```
  **This confirms §4's table entry that labeled `"Apple M6"` as merely "pattern-inferred."
  It's not a guess anymore — it's the device tree's own `SoC Name`, which is exactly what
  feeds `sysctl -n machdep.cpu.brand_string` on real hardware.** Downgrade that fixture's
  label from `_PATTERN_INFERRED` to a plain, confirmed value if you build it.
- The device tree's other identity-shaped fields (`mlb-serial-number`,
  `model-number`, `region-info`, `regulatory-model-number`, `config-number`) are all
  literal firmware placeholders — e.g. `"mlb-serial-number": "syscfg/MLB#/0x20,zeroes/0x20"`
  — not real device data. Nothing sensitive to redact here; this is Apple's own generic
  template, confirmed by inspecting the values before using them anywhere.
- `iBoot.j804.RELEASE.im4p` (extracted via `ipsw extract --iboot`), inspected with `ipsw
  img4 im4p info`: `Type: ibot`, `Version: mBoot-20457.41.3`, LZFSE-compressed, 4.4 MB
  uncompressed. `LLB.j804.RELEASE.im4p`'s manifest entry (from `BuildManifest.plist`
  directly, not re-extracted) gives `BuildString: iBoot-15391~1595`.
- `ipsw extract --kernel` produced a genuine 125 MB Mach-O 64-bit arm64 kernelcache
  (`file` confirms the type) — real binary, decrypted/decompressed by the tool, useful
  stock for `phase-5.md`'s eventual fuzzing corpus.
- **Confirmed limitation, not a tool failure:** `ipsw device-info --prod Mac18,1` (the
  cross-reference lookup §2 planned to use) returned `{}` — the installed tool's bundled
  device database predates M6's launch and hasn't been updated with `Mac18,1`/`Mac18,2`
  yet. The same lookup works fine for older devices (tested against `Mac15,11`). Track A's
  other commands don't depend on this database at all, so this doesn't block anything —
  it's just one cross-check that isn't available yet for this generation.
- **Confirmed, not assumed:** fed the real `iBoot.j804.RELEASE.im4p` into this project's
  own `state::img4::parse_manifest_der` (a one-off local test, not committed — the
  function expects `IM4M`, not `IM4P`, different ASN.1 schemas). It correctly returned
  `Err(Decode(...))` rather than silently misparsing it — the fail-closed behaviour
  `spec/build-spec.md` requires held up against a real, unexpected input type, not just
  the garbage-bytes test already in the suite.
- Output artifacts (BuildManifest.json, device tree JSON/summary, extracted im4p/
  kernelcache files, `ipsw info` dumps) are under `research/` in this repo, which is now
  `.gitignore`'d (added alongside `*.ipsw` — a 20.8 GB restore image and a 125 MB
  kernelcache binary have no business in git history). The `tests/fixtures/` entries §4
  describes were built from these real values (not placeholders) in a follow-up commit —
  see `tests/fixtures/README.md`'s `_FIRMWARE_TEMPLATE` section and `progress/milestones.md`.

## Results from Track B: the VM — blocked, and why

Attempted on 2026-11-10, same session as the Track A results above. Tool: `tart` v2.41.1
(the `cirruslabs/cli/tart` Homebrew formula was broken against this Homebrew version at
install time — `depends_on :macos` DSL error in the tap itself, not this project's doing —
so the binary was pulled directly from the project's GitHub release instead:
`gh release download 2.41.1 --repo cirruslabs/tart --pattern tart.tar.gz`, extracted, and
kept as an intact `.app` bundle rather than copying the raw Mach-O out — copying just the
binary trips Gatekeeper/AMFI and the process gets killed (exit 137); running it from
inside the bundle works, since its signature is notarized and tied to that bundle shape).

```
$ tart create m6-research-vm --from-ipsw=UniversalMac_27.2_26B7124_Restore.ipsw --disk-format asif
Error: UnsupportedRestoreImageError()
```

No partial VM was created (`tart list` confirms this — the error fires before any disk
allocation).

**Why, grounded in Apple's own documentation, not guessed:** `VZMacOSRestoreImage` can
contain installation media for multiple Mac hardware models, and Apple's docs state
plainly that its `mostFeaturefulSupportedConfiguration` property — the configuration tart
needs to proceed — is `nil` "if none of the hardware models are supported on the current
host." This IPSW's two `BuildIdentities` are both M6-generation (`Mac18,1`/`Mac18,2`,
`t8152`). **The host machine in this session is an Apple M2 Pro.** The strong inference —
backed by Apple's documented API behavior, though no error-string-exact source was found —
is that Virtualization.framework does not let a host create a VM targeting a *newer* SoC
generation's hardware model than the host's own silicon, independent of which macOS
*version* is involved. This is a different, and earlier, blocker than the one
`plans/research-environment.md`'s original §1 cited (SEP/LocalPolicy failing *inside* a
VZ guest) — that question is now moot for this host, because the VM can't be created at
all, for a more basic reason than SEP.

**What this means for `progress/goal.md`'s open question:** it isn't answered yet, just
blocked by a more fundamental constraint on this specific host. To actually test Track B
on this hardware, the IPSW would need to be for a chip generation at or older than the
host's own (M2 Pro or earlier) — which defeats the point of using it for M6-specific
research. The real path forward for Track B is **a host machine whose own chip is M6 or
newer**; absent that, this research track's honest conclusion is to pivot to
`plans/phase-3.md`'s real-scratch-hardware route for proving an actual security-mode
transition, same as `goal.md` already anticipated as a legitimate outcome.

## Sources

- [TechCrunch — Apple unveils new 14-inch MacBook Pro with M6 chip](https://techcrunch.com/2026/10/27/apple-unveils-new-14-inch-macbook-pro-with-m6-chip/)
- [MacRumors — M6 MacBook Pro Expected This Year With Apple's First 2nm Chip](https://macrumors.com/2026/06/25/m6-macbook-pro-2026/) (pre-launch reporting on no M6 Pro/Max this cycle)
- [TheAppleWiki — Mac18,1 / MacBook Pro (14-inch, M6)](https://theapplewiki.com/wiki/Mac18,1)
- [blacktop/ipsw — CLI docs](https://blacktop.github.io/ipsw/docs/cli/ipsw/)
- [img4tool README (IM4P/IM4M/personalization split)](https://github.com/karakaslar2/img4tool)
- [khronokernel — Apple Silicon and Virtual Machines: Custom Serials, DEP Enrolment and the Secure Enclave](https://khronokernel.com/macos/2023/08/18/AS-VM-SERIAL.html)
- [Apple Developer Forums — "Entering 1TR with Virtualization.framework?"](https://developer.apple.com/forums/thread/699102) (SEP/LocalPolicy failure report in VZ guests)
- [cirruslabs/tart — `--from-ipsw` VM creation](https://github.com/cirruslabs/tart)
- [Apple Developer Docs — `VZMacOSRestoreImage.mostFeaturefulSupportedConfiguration`](https://developer.apple.com/documentation/virtualization/vzmacosrestoreimage.md) (nil "if none of the hardware models are supported on the current host" — the basis for this document's inferred cause of `UnsupportedRestoreImageError`)
