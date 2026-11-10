# Milestones

Tracks progress toward `goal.md`. Read that file first — every milestone here exists in
service of it.

## How to record progress (read before editing)

- **Update the status table** when a milestone's state changes, and **append a dated
  entry** to the log below it — don't just flip a status with no record of what happened.
- Every "Done" needs evidence: a commit hash, a file path, or both. No commit/file to
  point to means it isn't done yet — write "In progress" and say what's blocking it
  instead. This mirrors `spec/build-spec.md` golden rule 8 (no claim without a fresh
  measurement) applied to this project's own tracking, not just the tool it builds.
- If a milestone turns out to be impossible or needs to be split/reordered, say so in the
  log rather than silently deleting or renumbering it — the history of "we thought X, then
  found Y" is as valuable as the final state.
- New milestones get appended at the end of the table with the next free `M<n>`, not
  inserted into the middle — keeps old log entries' references stable.

## Status

| # | Milestone | Status | Evidence |
|---|---|---|---|
| M0 | Research environment plan written (`plans/research-environment.md`) | Done | commit `f68c6d4` |
| M1 | Real IPSW ground-truth extraction — Track A (`ipsw info`/`plist`/`dtree` against `UniversalMac_27.2_26B7124_Restore.ipsw`) | Done | commit `6b40e36`; results recorded in `plans/research-environment.md`'s "Results from the real IPSW" |
| M2 | M6 identity fixtures committed (`tests/fixtures/*_M6*`) | Done | commit `6b40e36` |
| M3 | `authorize`/`execute`/`verify` mutation pipeline implemented and proven on *some* target (real scratch hardware or VM, per `plans/phase-3.md`) | Not started | — |
| M4 | A macOS VM built from the real IPSW, owned/controlled by this project (`plans/research-environment.md` Track B) | **Blocked** — `tart create --from-ipsw` fails with `UnsupportedRestoreImageError()` on this host | `plans/research-environment.md`'s "Results from Track B"; `progress/goal.md`'s updated open-question section |
| M5 | Determined whether `bputil`'s mutation path (SEP/LocalPolicy) actually works inside that VM | Moot on this host — superseded by M4's earlier, more fundamental block; open again only if a newer-chip host becomes available | see M4's evidence |
| M6 | End-to-end proof: `evaluate` → `plan` → `apply` → `verify` inside the VM, with `verify` reporting a real non-`Full` `security_mode` | **Done** (manually, with real `bputil`/`csrutil` — not yet through the `bputil-eval` binary itself, whose `authorize`/`execute`/`verify` remain P3 stubs per `CLAUDE.md`) | `research/vm_measure_25D125.log` (baseline), `research/vm_verify_postmutation_25D125.log` (post-mutation) |
| M7 | Written finding on why the VM path doesn't work, plus a decision on pursuing the same proof via `plans/phase-3.md`'s real scratch hardware instead | Decided: see M8 — a safer third option than either original branch, not a straight pivot to phase-3 | `progress/goal.md`'s "Decision, 2026-11-10" |
| M8 | A VM built from a chip generation this host *can* virtualize (`tart create --from-ipsw=latest`), not the M6 image — re-opens M5's question on hardware that can actually attempt it, with strictly less risk than real scratch hardware | In progress — local IPSW downloaded (18.9 GB, `CURL_EXIT:0`), `tart create` against it running | `research/curl_download_25D125.log`; `research/ipsw_downloads/UniversalMac_26.3_25D125_Restore.ipsw` |
| M9 | Determined whether `bputil`'s mutation path actually works inside *this* VM | **Done — yes, it works.** Both read (`bputil -d`) and mutation (`bputil -g -k -v <vuid>`, run live from the VM's recovery/1TR-equivalent by the user) succeeded, confirmed by a fresh post-reboot measurement | `research/vm_measure_25D125.log`, `research/vm_verify_postmutation_25D125.log` |
| M10 | Full `Reduced -> Full -> Permissive` round trip, evidenced by the real `bputil-eval` binary (not just raw `bputil`) run against the live VM, with a committed evidence bundle | **Done** | `evidence/vm-sec-research-25D125/` (hash-verified) |

## Log

### 2026-11-10 — M0, M1, M2 recorded as done

Installed `blacktop/ipsw` (brew) and ran it against the real
`UniversalMac_27.2_26B7124_Restore.ipsw` (20.8 GB, in the repo root, gitignored). Confirmed
first-hand: the IPSW supports exactly `Mac18,1` (MacBook Pro 14", board `J804AP`) and
`Mac18,2` (iMac 24", board `J833ctAP`), both plain M6 (`t8152`, ARMv9.5-A) — no Pro/Max
tier, matching `plans/research-environment.md` §0's naming concern. Extracted
`BuildManifest.plist`, ran `ipsw dtree --filter j804ap`, extracted `iBoot`/kernelcache,
and one-off-tested that `state::img4::parse_manifest_der` correctly rejects a real IM4P
(it expects IM4M) rather than misparsing it.

Built four fixtures from the confirmed values (`sysctl_machdep_cpu_brand_string_M6.txt`,
`sw_vers_buildVersion_M6.txt`, two `_FIRMWARE_TEMPLATE` identity fixtures) and introduced
the `_FIRMWARE_TEMPLATE` labeling convention in `tests/fixtures/README.md` for data that's
real but comes from unpersonalized firmware rather than a live device. 44 tests pass,
clippy/fmt/guards clean.

`progress/` itself (this file and `goal.md`) created in the same session, to track the
rest of this goal going forward — M3 onward are genuinely not started yet; this entry
doesn't claim otherwise.

**Next up:** M4 (boot the VM via `tart create --from-ipsw=...`, per
`plans/research-environment.md` §3) is the next unblocked milestone — M3 can proceed in
parallel since it doesn't depend on the VM existing yet, only on having *some* target to
eventually run the round trip against.

### 2026-11-10 — M4 attempted, blocked; M5 moot on this host; M7's finding written

Installed `tart` (the Homebrew formula is currently broken against this Homebrew version
— pulled the v2.41.1 binary from the project's GitHub release instead; see
`plans/research-environment.md` for the exact steps, including the Gatekeeper/AMFI gotcha
of copying the raw binary out of its `.app` bundle). Ran:

```
tart create m6-research-vm --from-ipsw=UniversalMac_27.2_26B7124_Restore.ipsw --disk-format asif
```

Result: `Error: UnsupportedRestoreImageError()`, no partial VM created. Root cause,
grounded in Apple's own `VZMacOSRestoreImage` documentation (not guessed): the host in
this session is an Apple M2 Pro, and this IPSW's only build identities are M6-generation
(`Mac18,1`/`Mac18,2`) — Apple's docs say the configuration tart needs comes back `nil`
when the host supports none of a restore image's hardware models. A VM targeting a newer
chip generation than the host's own apparently can't be created at all, independent of
the SEP/LocalPolicy question M5 was originally meant to test.

This makes M5 moot *on this specific host* — not answered, just blocked one layer
earlier than expected. Wrote up the full reasoning in
`plans/research-environment.md`'s "Results from Track B" and the corresponding update to
`progress/goal.md`'s open-question section (M7's "written finding" half). The remaining
open decision — try Track B again on a host with an M6-or-newer chip, versus pivot to
`plans/phase-3.md`'s real-scratch-hardware route — is left for whoever picks this up next;
nothing here commits to one.

**Next up:** either (a) get access to a host whose own chip is M6 or newer and retry M4,
or (b) decide to pursue M3/M6's "verify an unlock" proof via real scratch hardware
(`plans/phase-3.md`) instead and treat the VM track as concluded for now. M3 (the
`authorize`/`execute`/`verify` pipeline itself) remains unblocked either way and can still
be built in parallel.

### 2026-11-10 — M8 started: a safer third option than either branch above

User asked for a safer option than real scratch hardware. Rather than wait for M6-or-newer
hardware or move to physically risky scratch hardware, retrying Track B with an IPSW for
a chip generation *this host can actually virtualize* removes the M4 blocker entirely
while staying fully disposable — no physical device, no DFU-restore exposure, no real
credentials at stake. Ran:

```
tart create vm-sec-research --from-ipsw=latest --disk-format asif
```

(`latest` fetches Apple's own latest-supported-for-this-host image, so it should avoid
`UnsupportedRestoreImageError()` by construction.) Running in the background at the time
of this entry — not yet confirmed to succeed. `progress/goal.md` updated with the
reasoning for this option under "Decision, 2026-11-10."

**Next up:** confirm the VM actually creates and boots, then start on `bputil -d`/`sudo
bputil -g` etc. inside it to answer M9 — the real open question this whole track exists to
answer.

### 2026-11-10 (continued) — M8: `tart --from-ipsw=latest` failed twice, pivoted to a direct, resumable download

First attempt (`--from-ipsw=latest`, resolved to `UniversalMac_26.6.2_25G83`) failed
mid-download: `Error: The network connection was lost.` at 41%. Retried the same way;
failed again at 70% with the identical error. Root cause for *that* specific error turned
out not to matter in the end (see below), but along the way: `tart` doesn't resume a
dropped download, so each retry restarted from zero bytes, and it also doesn't clean up a
stale cached download on failure — a leftover 18GB partial sat in `~/.tart/cache/IPSWs/`
until manually deleted (with the user's confirmation, per the host-impact policy now in
`CLAUDE.md`).

Separately, the install itself also failed once, independent of the network issue:
`Error: A software update is required to complete the installation.` A real, grounded
explanation (via web research, not guessed): this is a known `VZErrorDomain` pattern when
the host is missing newer "device support" files a given guest restore image needs —
consistent with a Homebrew warning seen earlier in this session that this host's Xcode
(26.6) is outdated vs. 27.0. Rather than update Xcode (a real host-level change), picked
the lower-impact fix: target the *exact* IPSW build this host is already running
(`UniversalMac_26.3_25D125`, confirmed via `sw_vers` to match this host precisely) instead
of whatever `latest` resolves to — found via `ipsw download ipsw --macos --version 26.3
--urls` (read-only lookup, no download).

That exact-match download then *also* hit `The network connection was lost` (via `tart`
directly), then `ipsw download ipsw`'s own downloader failed differently — "initial
request... failed" with no detail, at the very first byte, while a plain `curl -I` to the
identical URL succeeded immediately after. That isolated the problem to the two tools'
downloader implementations, not the network or the URL. Pivoted to a direct `curl -C -
--retry 5 --retry-delay 5` download (resume + auto-retry in one invocation, and `curl`'s
already been proven reliable against this exact URL) — in progress as of this entry, not
yet confirmed complete. Once the file lands locally, `tart create
--from-ipsw=<local-path>` against it is the next step.

**Next up:** confirm the `curl` download completes, then `tart create --from-ipsw=` the
local file and retry M8. This entry exists so the next session (or the next context
window) doesn't repeat the same two failed downloader paths from scratch.

### 2026-11-10 (continued) — M8: confirmed the curl download actually finished; retrying `tart create` against the local file

Picked this back up in a fresh session. The curl download that was "in progress, not yet
confirmed complete" at the end of the previous entry had, in fact, already finished
successfully by the time this session started: `research/curl_download_25D125.log` ends
with `100 17.5G 100 17.5G ... CURL_EXIT:0`, and the file on disk
(`research/ipsw_downloads/UniversalMac_26.3_25D125_Restore.ipsw`) is 18,877,622,182 bytes
and reads as a valid zip archive (`file` confirms `Zip archive data`). Confirmed this host
is still exactly `26.3`/`25D125` (`sw_vers`), so this is still the exact-match IPSW
targeted deliberately to dodge the earlier `VZErrorDomain` "software update required"
failure. Disk headroom checked before proceeding: `/System/Volumes/Data` had 90 GB free
(808 GB used of 926 GB) — noted as tight but likely sufficient; being watched as the VM
build runs, since a macOS VM install can be disk-hungry and this is a host-level disk
commitment that needs tracking per `CLAUDE.md`'s host-impact rule.

Started `tart create vm-sec-research-25D125 --from-ipsw=research/ipsw_downloads/UniversalMac_26.3_25D125_Restore.ipsw --disk-format asif` in the background, logging to
`research/tart_create_25D125_local.log`.

**Result: success.** `TART_EXIT:0`, progress reached 100%. `tart list` confirms:
`vm-sec-research-25D125`, 50 GB disk, 22 GB accessed, state `stopped`. This clears the M4
blocker for this chip generation — `UnsupportedRestoreImageError()` doesn't occur for an
IPSW matching the host's own chip generation (M2 Pro / `26.3`/`25D125`), consistent with
`plans/research-environment.md`'s inferred cause. Disk headroom after creation:
67 GB free (was 90 GB before create, 90 GB before the download even landed) — tight but
not exhausted; worth re-checking before any further disk-growing step (first boot/install
can grow the APFS container further even though `asif` is sparse).

**Next up:** `tart run vm-sec-research-25D125` to boot it. Expect this needs to run
through to completion of first-boot setup, which likely requires either VNC
(`tart run --vnc`) or GUI interaction with the window tart opens, since a fresh macOS VM's
Setup Assistant isn't scriptable the way tart's own pre-built CI base images are. Once
booted to a point SSH or screen sharing works, the real M9 steps are `csrutil status` and
`sudo bputil -d` (or `-g`) inside the guest.

### 2026-11-10 (continued) — M8: VM booted; blocked on a genuine tool-access gap, not a research finding

Ran `tart run vm-sec-research-25D125` (backgrounded, PID confirmed alive via `ps`) — this
opens a real GUI window on this host's own screen via Virtualization.framework, the same
as it would if a person ran it themselves from Terminal. Checked this session's available
tools before assuming further progress was possible: no `mcp__computer-use__*` tools are
present (confirmed via a tool search, not assumed), meaning this session — Claude Code
running in a terminal — has no way to see or click the VM's Setup Assistant screens itself.
`--provisioning-opts` (which would script first-boot account creation + Remote Login
non-interactively) requires the *host* to run macOS 27+; this host is 26.3, so that path is
unavailable too, confirmed from `tart run --help`'s own text, not guessed.

This is a tooling-access boundary, not a finding about the VM/bputil question itself —
recording it as such rather than conflating the two. The VM is sitting at (or near) macOS's
Setup Assistant on this host's real screen right now, waiting for a human to click through
language/region/skip-Apple-ID/create-a-local-account, then run
`sudo systemsetup -setremotelogin on` once at the Desktop (or enable Remote Login via
System Settings → General → Sharing) so this session can SSH in
(`tart ip vm-sec-research-25D125` for the address) and run the actual M9 commands
(`csrutil status`, `sudo bputil -d`) without further GUI access.

**Next up:** needs a human (this session's user) to complete Setup Assistant once and
enable Remote Login inside the guest. Not blocked on anything else — the VM itself is
healthy and booting.

### 2026-11-10 (continued) — M9: SEP/LocalPolicy communication confirmed working inside this VM — a real, grounded answer, not a guess

User completed Setup Assistant (local account `test`/short-name lowercased from the
Full Name typed in Setup Assistant — note for next time: macOS derives the Unix short
name by lowercasing, so SSH as `test`, not `Test`) and enabled Remote Login. Port 22
confirmed open (`nc -zv` after an initial `No route to host` — Remote Login hadn't been
flipped on yet at that point, consistent with "still mid-setup," not a bug). SSH'd in via
`expect` (password auth, `StrictHostKeyChecking=no` for a known-fresh host key) and ran,
inside the guest:

```
sw_vers              -> ProductVersion: 26.3, BuildVersion: 25D125 (matches the IPSW exactly)
sysctl -n machdep.cpu.brand_string -> "Apple M2 Pro (Virtual)" — confirms
                         plans/research-environment.md §1's prediction: virtualized/generic
                         identity, not the real host chip string verbatim, not M6
csrutil status       -> "System Integrity Protection status: enabled."
sudo bputil -d        -> full, real local-policy dump — NOT a SEP-communication error
```

**This is the answer to the open question `goal.md` has carried since M4/M5, grounded in
a real measurement on real (if virtualized) Apple hardware, not inferred:** the Apple
Developer Forums report that `bputil -d` fails inside a VZ guest with a "Failed to create
local policy" SEP error does **not** reproduce on this host (Apple M2 Pro, macOS 26.3) /
`tart` v2.41.1 / guest macOS 26.3 combination. `bputil -d`'s output shows `OS Pairing
Status: Paired` and a fully-populated local policy — SEP/LocalPolicy communication works.
Decoded baseline state (several fields print as the Apple-documented default when their
manifest entry is `absent`, which is itself informative — it means no policy override has
ever been written): `Security Mode: Full`, `3rd Party Kexts Status: Disabled`, `SIP
Status: Enabled`, `Signed System Volume Status: Enabled`, `Kernel CTRR Status: Enabled`,
`Boot Args Filtering Status: Enabled` — i.e. a clean `Full` baseline, exactly what
`goal.md`'s "What success looks like" step 1 asks for as the starting point.

Also ran `bputil -h` (first 20 lines) to confirm `-u`/`-p` username/password flags exist
for non-interactive credential passing — relevant to the next step, but **deliberately not
used yet**: this session already automated the *evaluate*-side credentials (SSH password,
`sudo -S` for the read-only `-d` call) via an `expect` script, which is fine for a read-only
measurement, but `spec/build-spec.md` golden rule 4 is explicit that an actual mutation
(`apply`) needs a live, typed owner confirmation that is never scripted/automated by the
tool or the agent driving it — and real `bputil` mutations are documented to require
running from 1TR (`tart run --recovery` is the likely VM-side equivalent, not yet tried).
Stopping here deliberately rather than scripting a mutation call next.

**Net result for `goal.md`'s open technical question:** answered, for this host/OS
combination — SEP/LocalPolicy does not fail in this VZ guest. This reopens the real
possibility of completing M6's full `evaluate -> plan -> apply -> verify` round trip
*inside a VM*, which `plans/research-environment.md` had treated as foreclosed pending
newer hardware. Whether the *mutation* path specifically also works (not just the read
path) is still open — that's M9's remaining half.

**Next up:** decide, with the user, whether to attempt the actual mutation step
(`tart run --recovery` equivalent of 1TR, then `bputil` with a human-present, live-typed
owner confirmation — not scripted) now, or treat the read-path confirmation above as
sufficient evidence for this milestone and pause before touching the mutating half, which
is categorically more consequential per the golden rules.

### 2026-11-10 (continued) — M9 mutation half + M6: attempted the real `apply` step, live, with the user typing owner confirmation

User chose to continue. Stopped the running VM (`tart stop`), booted it with
`tart run --recovery`. Confirmed — via the user running commands directly in the Recovery
window's own Terminal, not via anything scripted by this session — that this is genuinely
the paired-recovery (1TR-equivalent) environment: `whoami` returned `root` (Recovery's
Terminal has no login) and `/System/Library/CoreServices/Finder.app` does **not** exist
(the primary signal `env.rs`'s doc comment, per `CLAUDE.md`, says to check first).

**Secondary finding, worth flagging for whoever next touches `env.rs`:** `CLAUDE.md`'s
documented 1TR-detection fallback says `bputil -d`'s "OS Type" line should read "one true
recoveryOS" when paired vs. "ordinary recovery OS" in fallback. That is **not** what this
real `bputil` (v0.1.14, macOS 26.3) prints — it printed `OS Type: macOS (overridden)`
identically in both the normal-OS run and this recovery run. That field evidently
describes the *paired target OS* of the local policy, not the *current boot environment*
— it does not vary with boot context the way the doc comment assumed. This doesn't change
`env.rs`'s actual implementation (Finder.app-presence is still the primary, and apparently
sufficient, check — confirmed working above), but the text-parsing fallback description in
`CLAUDE.md` is now known to describe a string this real tool doesn't produce. Left as a
finding, not fixed, since `env.rs`'s primary path already works and changing doc comments
based on a VM-equivalent 1TR rather than real hardware felt like the wrong moment to firm
that up further.

Got the current container's volume group UUID from the earlier `bputil -d` capture
(`EAB17EE3-38E4-4EB5-9DA8-603399A81E90`) and matched it against this project's own
`plan.rs`: `Full -> ReducedKexts` plans exactly `bputil -g -k -v <vuid>` (confirmed via its
own golden-file tests, `tests/fixtures/plans/full_to_reduced_kexts.json` — not reconstructed
from memory). Gave the user that exact command to type themselves in the Recovery
Terminal, deliberately not scripting it (golden rule 4) — including correcting a
username mix-up (the account's *display* name was "Test Test"; `bputil`'s username prompt
needs the POSIX short name, `test`, the same one SSH used).

**User ran `bputil -g -k -v EAB17EE3-38E4-4EB5-9DA8-603399A81E90` live, typing the `test`
account's credentials themselves at `bputil`'s own interactive prompt, and reported it
printed success.**

Per golden rule 8, `bputil`'s own success message is not itself the evidence this project
requires — a fresh measurement from a normal boot is. **Not yet done as of this entry.**

**Next up:** reboot the VM out of recovery into the normal OS (`tart stop` +
`tart run`), SSH back in once Remote Login is reachable, and re-run `csrutil status` /
`sudo bputil -d` to get the fresh post-mutation measurement. Only *that* output, not this
entry, can close out M6's "evaluate -> plan -> apply -> verify" round trip and M9 in full.

### 2026-11-10 (continued) — M6 and M9: closed, with a real fresh measurement

Rebooted the VM out of recovery (`tart stop` then plain `tart run`), waited for Remote
Login to come back up (confirmed via `nc -zv` polling, ~5s), SSH'd in again, and ran
`csrutil status` + `sudo bputil -d` fresh — no caching, no reuse of the recovery-session
output.

**Result:** `Security Mode: Reduced (smb0): 1` and `3rd Party Kexts Status: Enabled
(smb2): 1` — both fields that printed `absent` (defaulted-Full) in every prior capture on
this VM now carry an explicit, signed value. The Local Policy Nonce Hash also changed
(`166F6210...` vs. the baseline's `67C723D2...`) and `Cryptex1 Generation (stng)` went from
`1` to `2` — both consistent with a genuinely new, re-signed local policy rather than a
stale read. `csrutil status` still reports SIP enabled, matching `ReducedKexts`'s expected
effect (SIP/SSV stay on; only third-party-kext trust changes) — exactly what `plan.rs`'s
`commands_for(TargetProfile::ReducedKexts, ...)` predicted before any of this ran.

**This closes `progress/goal.md`'s "What success looks like" checklist in full, against a
VM this project built and controls, not real M6 hardware:**
1. `evaluate`-equivalent baseline: `Security Mode: Full` (fields absent/defaulted) — ✅ (`research/vm_measure_25D125.log`)
2. `plan`-equivalent: `bputil -g -k -v <vuid>`, matching `plan.rs`'s own committed golden file for `Full -> ReducedKexts` — ✅
3. VM's 1TR-equivalent (recovery, confirmed paired via `whoami`=`root` + absent `Finder.app`), owner-present, live-typed confirmation, never scripted by this session — ✅
4. Fresh `verify`-equivalent measurement showing the new, non-`Full` `security_mode` — ✅ (this entry)

**What this does *not* yet mean:** `src/authorize.rs`/`execute.rs`/`verify.rs` are still
P3 stubs — none of this ran through the actual `bputil-eval` binary; it was done with the
real Apple tools directly, by hand, with the user as the live owner. What it *does* mean,
concretely, for `CLAUDE.md`'s "Repository status" section (not edited here, since that's
project doctrine rather than a progress log, but worth flagging explicitly): the stated
reason P3 has been deliberately left unstarted — "needs a human physically rebooting into
1TR to enter owner credentials, none of which this agent can do unattended" — has a
narrower version now demonstrably satisfiable **with a human present or on-call for the
`apply`/`revert` step**, via a disposable VM instead of real scratch hardware. Whether
that's enough to start P3's actual Rust implementation is a decision for the user, not
assumed here.

**Not yet done:** the revert half of the round trip (`Reduced -> Full`, via `bputil -f -v
<vuid>` per `plan.rs`'s own golden file) — `goal.md`'s checklist above doesn't require it,
but `spec/phased-plan.md`'s P3 exit gate explicitly wants "full→reduced→full" as a round
trip, and golden rule 5 requires a revert path to always exist. Left for a follow-up
session or immediate continuation, at the user's call — the VM is still running, `Reduced`,
reachable over SSH.

### 2026-11-10 (continued) — M10: full round trip to `Permissive`, evidenced by the real `bputil-eval` binary, bundle committed under `evidence/`

User asked to continue further — "open the bootloader" (this project's own vocabulary,
per `reports/m2-bootloader-unlock-technicians-guide.md` §2, for the `Permissive`
custom-kernel-capable security mode, the deepest point on the `Full/Reduced/Permissive`
spectrum) — and to demonstrate the result as a real evidence bundle, not just terminal
output.

**Built the release binary** (`cargo build --release`) — confirmed `arm64` Mach-O,
matching the VM's architecture exactly (same chip family, and this VM's macOS build is
identical to the host's: `26.3`/`25D125`). Copied it onto the VM over `scp` and ran it
*from the VM itself*, over SSH — this is the first time in this research track that the
actual `bputil-eval` tool (not hand-typed `bputil`) measured a live target.

1. **Baseline, live tool:** `bputil-eval evaluate --json` against the already-`Reduced`
   VM confirmed `security_mode: "Reduced"`, `allows_third_party_kexts: true`,
   `allows_custom_kernel: false` — matching `plan.rs`'s predicted invariants exactly, not
   just raw `bputil -d` output. `bputil-eval report --session-id reduced-baseline` wrote a
   first evidence bundle.
2. **Revert, live owner:** rebooted to recovery; user ran `bputil -f -v
   EAB17EE3-38E4-4EB5-9DA8-603399A81E90` themselves, typing credentials live. Fresh
   `bputil -d` in that same recovery session (screenshotted by the user, not scripted)
   confirmed `Security Mode: Full (smb0): absent`, `3rd Party Kexts Status: Disabled`,
   nonce hash changed, `Cryptex1 Generation` incremented `2 -> 3`.
3. **Permissive, live owner:** same session, user ran `bputil -n -c -s -v
   EAB17EE3-38E4-4EB5-9DA8-603399A81E90`. Confirmed via screenshot:
   `Security Mode: Permissive (smb0 && smb1): 1`, `Signed System Volume Status: Disabled`,
   `Kernel CTRR Status: Disabled`, `SIP Status: Enabled` (unaffected, as `plan.rs` predicts
   — only SSV/CTRR/mode change under `PermissiveCustomKernel`, not SIP itself). Nonce hash
   changed again, `Cryptex1 Generation` `3 -> 4`.
4. **Fresh verify, live tool:** rebooted to normal macOS, SSH'd back in, ran
   `bputil-eval evaluate --json` (confirmed `security_mode: "Permissive"`,
   `ssv_enabled: false`, `allows_custom_kernel: true`) and
   `bputil-eval verify --baseline <Reduced-state evaluate output> --json`, which produced
   the tool's own structured diff:
   ```
   target_container.security_mode:        Reduced -> Permissive
   target_container.ssv_enabled:          true -> false
   target_container.allows_custom_kernel: false -> true
   ```
   `bputil-eval report --session-id permissive-final` wrote the second evidence bundle.

**Tooling finding, worth recording:** the VM's own on-disk copy of the intermediate
`~/baseline_reduced.json` (written via `evaluate --json > file` right after step 1) was
**not present** after the two subsequent `tart stop` / recovery-reboot cycles, even though
`~/bputil-eval` and `~/evidence/reduced-baseline/*` (written in the same session, same
disk) both survived intact. Root cause not confirmed — recorded as an open observation,
not a diagnosed bug, since it didn't block this session (the file's content was recovered
from this session's own captured terminal log instead, not re-derived or guessed, and its
hash was verified consistent). Worth a closer look before relying on a `tart` VM's disk as
durable scratch storage across recovery-mode reboots specifically.

**All four files' hash chains verified locally** (`shasum -a 256 -c`) before committing —
see `evidence/vm-sec-research-25D125/README.md` for the full bundle manifest and what it
does/doesn't prove. This is the first evidence in this project produced by the actual
`bputil-eval` binary against a live, mutated target — previously all measurements in this
track used raw `bputil`/`csrutil` directly. `authorize`/`execute`/`verify.assert_invariants`
(P3) still did not run any of it; every mutating command was typed live by the user.

**Next up:** none required for M8/M9/M10 as scoped — all closed. Possible follow-ups, not
started: complete the round trip back to `Full` (for golden rule 5's "a revert path must
always exist" in its fullest sense); investigate the `baseline_reduced.json` persistence
finding above; or move toward wiring `authorize`/`execute`/`verify.assert_invariants` (P3)
now that a disposable target proven to round-trip exists — a decision for the user, not
assumed here, per `CLAUDE.md`'s existing P3 boundary discussion.
