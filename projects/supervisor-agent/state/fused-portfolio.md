# Fused portfolio view

Regenerated from `state/portfolio.db` — the machine-extracted,
provenance-carrying view of every parsed source (BUILD-SPEC §3: the
database is the single source of truth; this mirror is a view). Never
edited by hand; a divergence would be a `sync_violations` row and the
database wins every such fight.

Regenerated: 2026-11-10T15:30:16Z

## Initiatives

| slug | kind | status | owner_gate | proposal_ref |
|---|---|---|---|---|
| project1_fuzz | project1_fuzz | pre-build | user_gated | projects/01-continuous-fuzz-bug-hunter/PROPOSAL.md |
| project2_mutation | project2_mutation | pre-build | user_gated | projects/02-gated-mutation-engine/PROPOSAL.md |
| project3_drift | project3_drift | pre-build | user_gated | projects/03-fleet-drift-watch/PROPOSAL.md |
| supervisor | supervisor | pre-build | — | projects/supervisor-agent/PROPOSAL.md |
| vm_sec_research | vm_sec_research | active | — | progress/goal.md |
| vulnres_suite | vulnres_suite | active | — | vuln_res/README.md |

## Milestones (verbatim from progress/milestones.md)

| ref | title | status | evidence |
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

## Milestone log (dated entries; 'Next up' = decision-engine input)

- **2026-11-10 — M0, M1, M2 recorded as done** (touches: M0, M1, M2)
  - next-up: M4 (boot the VM via `tart create --from-ipsw=...`, per `plans/research-environment.md` §3) is the next unblocked milestone — M3 can proceed in parallel since it doesn't depend on the VM existing yet, only on having *some* target to eventually run the round trip against.
- **2026-11-10 — M4 attempted, blocked; M5 moot on this host; M7's finding written** (touches: M4, M5, M7)
  - next-up: either (a) get access to a host whose own chip is M6 or newer and retry M4, or (b) decide to pursue M3/M6's "verify an unlock" proof via real scratch hardware (`plans/phase-3.md`) instead and treat the VM track as concluded for now. M3 (the `authorize`/`execute`/`verify` pipeline itself) remains unblocked either way and can still be built in parallel.
- **2026-11-10 — M8 started: a safer third option than either branch above** (touches: M8)
  - next-up: confirm the VM actually creates and boots, then start on `bputil -d`/`sudo bputil -g` etc. inside it to answer M9 — the real open question this whole track exists to answer.
- **2026-11-10 — M8: `tart --from-ipsw=latest` failed twice, pivoted to a direct, resumable download** (touches: M8)
  - next-up: confirm the `curl` download completes, then `tart create --from-ipsw=` the local file and retry M8. This entry exists so the next session (or the next context window) doesn't repeat the same two failed downloader paths from scratch.
- **2026-11-10 — M8: confirmed the curl download actually finished; retrying `tart create` against the local file** (touches: M8)
  - next-up: `tart run vm-sec-research-25D125` to boot it. Expect this needs to run through to completion of first-boot setup, which likely requires either VNC (`tart run --vnc`) or GUI interaction with the window tart opens, since a fresh macOS VM's Setup Assistant isn't scriptable the way tart's own pre-built CI base images are. Once booted to a point SSH or screen sharing works, the real M9 steps are `csrutil status` and `sudo bputil -d` (or `-g`) inside the guest.
- **2026-11-10 — M8: VM booted; blocked on a genuine tool-access gap, not a research finding** (touches: M8)
  - next-up: needs a human (this session's user) to complete Setup Assistant once and enable Remote Login inside the guest. Not blocked on anything else — the VM itself is healthy and booting.
- **2026-11-10 — M9: SEP/LocalPolicy communication confirmed working inside this VM — a real, grounded answer, not a guess** (touches: M9)
  - next-up: decide, with the user, whether to attempt the actual mutation step (`tart run --recovery` equivalent of 1TR, then `bputil` with a human-present, live-typed owner confirmation — not scripted) now, or treat the read-path confirmation above as sufficient evidence for this milestone and pause before touching the mutating half, which is categorically more consequential per the golden rules.
- **2026-11-10 — M9 mutation half + M6: attempted the real `apply` step, live, with the user typing owner confirmation** (touches: M6, M9)
  - next-up: reboot the VM out of recovery into the normal OS (`tart stop` + `tart run`), SSH back in once Remote Login is reachable, and re-run `csrutil status` / `sudo bputil -d` to get the fresh post-mutation measurement. Only *that* output, not this entry, can close out M6's "evaluate -> plan -> apply -> verify" round trip and M9 in full.
- **2026-11-10 — M6 and M9: closed, with a real fresh measurement** (touches: M6, M9)
  - next-up: —
- **2026-11-10 — M10: full round trip to `Permissive`, evidenced by the real `bputil-eval` binary, bundle committed under `evidence/`** (touches: M10)
  - next-up: none required for M8/M9/M10 as scoped — all closed. Possible follow-ups, not started: complete the round trip back to `Full` (for golden rule 5's "a revert path must always exist" in its fullest sense); investigate the `baseline_reduced.json` persistence finding above; or move toward wiring `authorize`/`execute`/`verify.assert_invariants` (P3) now that a disposable target proven to round-trip exists — a decision for the user, not assumed here, per `CLAUDE.md`'s existing P3 boundary discussion.

## Evidence by kind

| kind | rows |
|---|---|
| commit_event | 26 |
| finding | 5 |
| knowledge | 4 |
| milestone | 10 |
| sweep_summary | 3 |

## Links

- `bears-on`: 16

## Parse health

- parse_failures rows (all-time, first-class history): 2
- parse_failures today: 2

## Sweep ledger (parsed)

| sweep | kind | started | new findings (verbatim) |
|---|---|---|---|
| 2026-11-10-001-recon-verification | recon | 2026-11-10 | 2 — [`ssv-enabled-contains-whole-blob`](./2026-11-10-001-recon-verification/ssv- |
| 2026-11-10-002-fallback-and-audit | recon | 2026-11-10 | 0 (closed/root-caused the existing `agent-registry-not-live-this-session` |
| 2026-11-11-001-host-independent-parsing-hardening | recon | 2026-11-11 | 3 — [`security-mode-full-contains-whole-blob`](./2026-11-11-001-host-independent |

## Findings (verbatim from the cross-sweep index)

| finding | score | status |
|---|---|---|
| vuln_res/sweep-reports/findings-index.md#agent-registry-not-live-this-session | n/a (operational) | root-caused; harness feedback filed; working fallback documented |
| vuln_res/sweep-reports/findings-index.md#ci-guards-regex-boundary-gaps | n/a (operational) | fixed, self-test corpus added |
| vuln_res/sweep-reports/findings-index.md#security-mode-full-contains-whole-blob | 9 (3×1×3) | fixed, confirmed against real VM-captured `bputil -d` output |
| vuln_res/sweep-reports/findings-index.md#ssv-enabled-contains-whole-blob | 9 (3×1×3) | fixed (committed) |
| vuln_res/sweep-reports/findings-index.md#verify-baseline-no-size-cap | 2 (1×1×2) | fixed |

## Capabilities (parsed approval contracts)

| name | kind | approval_class |
|---|---|---|
| vulnres-disclosure | agent | autonomous |
| vulnres-environment-runner | agent | user_gated |
| vulnres-exploit-dev | agent | autonomous |
| vulnres-fuzz-harness | agent | user_gated |
| vulnres-orchestrator | agent | user_gated |
| vulnres-recon | agent | user_gated |
| vulnres-triage | agent | autonomous |

## Staleness clocks (state is data)

| surface | state | last_verified_at |
|---|---|---|
| environments:first-registered | never | never |
| fleet-enrollments:first-list | never | never |
| fuzz-targets:first-built | never | never |
| knowledge:build-test-clean | live | never |
| knowledge:cargo-audit-clean | live | never |
| knowledge:command-enum-note | live | never |
| knowledge:owner-credentials-cleared | live | never |
| vuln_res:agent-registry-fallback | invalid | 2026-11-10 |

## Implication: clock invalidations

- `vuln_res:agent-registry-fallback` invalidated by 0479b5b5e7a8e347fc19ff20ee1945223f168b6a — feat: fail-closed SSV status parsing; log M6/M9 VM mutation proof; add vuln-res agent framework
- `vuln_res:agent-registry-fallback` invalidated by 65a2736689510d56d9538646d7ea737b9adb00df — docs: root-cause the vulnres-* agent-registry gap and document a working fallback
- `vuln_res:agent-registry-fallback` invalidated by 86ce5fa96b0a2579e39f4ca50f1be6b0744f88c0 — feat: add vulnres-pattern-analysis and vulnres-reporting skills, exploits-index.md

## Contradictions (loser marked, history kept)

- [R2] R2: currency claim [vuln_res/knowledge/INDEX.md#-[build-test-clippy-fmt-clean-2026-11-10](./build-test-clippy-fmt-clean-2026-11-10.md)] (asserted 2026-11-10) vs finding [vuln_res/sweep-reports/findings-index.md#security-mode-full-contains-whole-blob] (score 9, "fixed, confirmed against real VM-captured `bputil -d` output") recorded by sweep 2026-11-11-001-host-independent-parsing-hardening (2026-11-11) — the claim loses; nothing deleted, the loser is marked here
- [R2] R2: currency claim [vuln_res/knowledge/INDEX.md#-[command-enum-name-collision-tool-note](./command-enum-name-collision-tool-note.md)] (asserted 2026-11-10) vs finding [vuln_res/sweep-reports/findings-index.md#security-mode-full-contains-whole-blob] (score 9, "fixed, confirmed against real VM-captured `bputil -d` output") recorded by sweep 2026-11-11-001-host-independent-parsing-hardening (2026-11-11) — the claim loses; nothing deleted, the loser is marked here
- [R2] R2: currency claim [vuln_res/knowledge/INDEX.md#-[cargo-audit-cargo-deny-not-installed](./cargo-audit-cargo-deny-not-installed.md)] (asserted 2026-11-10) vs finding [vuln_res/sweep-reports/findings-index.md#security-mode-full-contains-whole-blob] (score 9, "fixed, confirmed against real VM-captured `bputil -d` output") recorded by sweep 2026-11-11-001-host-independent-parsing-hardening (2026-11-11) — the claim loses; nothing deleted, the loser is marked here
- [R2] R2: currency claim [vuln_res/knowledge/INDEX.md#-[build-test-clippy-fmt-clean-2026-11-10](./build-test-clippy-fmt-clean-2026-11-10.md)] (asserted 2026-11-10) vs finding [vuln_res/sweep-reports/findings-index.md#verify-baseline-no-size-cap] (score 2, "fixed") recorded by sweep 2026-11-11-001-host-independent-parsing-hardening (2026-11-11) — the claim loses; nothing deleted, the loser is marked here
- [R2] R2: currency claim [vuln_res/knowledge/INDEX.md#-[command-enum-name-collision-tool-note](./command-enum-name-collision-tool-note.md)] (asserted 2026-11-10) vs finding [vuln_res/sweep-reports/findings-index.md#verify-baseline-no-size-cap] (score 2, "fixed") recorded by sweep 2026-11-11-001-host-independent-parsing-hardening (2026-11-11) — the claim loses; nothing deleted, the loser is marked here
- [R2] R2: currency claim [vuln_res/knowledge/INDEX.md#-[cargo-audit-cargo-deny-not-installed](./cargo-audit-cargo-deny-not-installed.md)] (asserted 2026-11-10) vs finding [vuln_res/sweep-reports/findings-index.md#verify-baseline-no-size-cap] (score 2, "fixed") recorded by sweep 2026-11-11-001-host-independent-parsing-hardening (2026-11-11) — the claim loses; nothing deleted, the loser is marked here

