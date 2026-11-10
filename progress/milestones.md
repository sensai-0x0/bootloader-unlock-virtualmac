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
| M6 | End-to-end proof: `evaluate` → `plan` → `apply` → `verify` inside the VM, with `verify` reporting a real non-`Full` `security_mode` | Not started; blocked on M3, M4, M5 | — |
| M7 | Written finding on why the VM path doesn't work, plus a decision on pursuing the same proof via `plans/phase-3.md`'s real scratch hardware instead | Decided: see M8 — a safer third option than either original branch, not a straight pivot to phase-3 | `progress/goal.md`'s "Decision, 2026-11-10" |
| M8 | A VM built from a chip generation this host *can* virtualize (`tart create --from-ipsw=latest`), not the M6 image — re-opens M5's question on hardware that can actually attempt it, with strictly less risk than real scratch hardware | In progress | — |
| M9 | Determined whether `bputil`'s mutation path actually works inside *this* VM | Not started; blocked on M8 | — |

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
