# TTP library — pinned baseline, selection rubric, re-pin procedure

BUILD-SPEC §5.2. This file is the human-readable record of what's pinned and why;
`meta` holds the machine-checked pin (tag/url/sha), `attack_releases.is_pinned` holds
the structural pin.

## Pinned release

**ATT&CK-v20.1**, published 2026-11-05. Verified against the real `mitre/cti` GitHub
release (not assumed from this spec's own prose) during this phase's build:
`gh api repos/mitre/cti/releases/tags/ATT%26CK-v20.1` confirms the tag exists and was
published on that date; `attack.mitre.org/resources/updates/` was fetched directly to
confirm the specific AI-enabled technique IDs, group/campaign updates, and the
T1195.001 major-version change BUILD-SPEC §5.2 names — every one checked out against
the real page, not taken on faith from a prior session's prose. The exact bundle URL
and SHA-256 are recorded in `meta` (`attack_pin_url`, `attack_pin_sha256`,
`attack_pin_tag`) by `tools/ttp_ingest.py` at ingest time.

Why this release is unusually pointed for this portfolio (BUILD-SPEC §5.2, confirmed
against the real MITRE update page):

- First AI-enabled adversary techniques: T1699 (Direct Prompt Injection), T1698
  (Indirect Prompt Injection), T1700 (AI-Enabled Exfiltration), T1696 + T1696.001/.002
  (Anti-Automation Evasion), T1685.007 (Impair Autonomous Defenses), T1608.007 (AI
  Result Poisoning), T1697 (Steal Application-Specific Passwords) — several target
  agent-driven defensive pipelines like this portfolio's own agent fleet.
- T1195.001 (Compromise Software Dependencies and Development Tools) promoted v1.3 ->
  v2.0 — the exact class of threat this repo's own `Cargo.lock`-watching staleness
  infra exists for.
- New groups G1059 (NIMBUS MANTICORE), G1058 (The Gentlemen); major version bumps
  G1045 Salt Typhoon (v1.0->v2.0), G0082 APT38 (v3.1->v4.0); campaigns C0064
  ("AI-Assisted Breach of Mexico's Government Infrastructure") and C0066 ("2026 U.S.
  Water Utilities Attacks").

## Storage scope

**All** Enterprise techniques' IDs/names/tactics/platforms land in `techniques` +
`technique_tactics` + `technique_platforms` — the full catalog, so `v_technique_phase`
and future re-pin diffs have a complete base to compare against. **Only** the mapped
subset below gets a `ttp_mappings` row.

## Selection rubric — what gets mapped

A technique earns a `ttp_mappings` row only if it targets a surface this portfolio
**actually has today or is scheduled to build** (its own `PROPOSAL.md` exists and
names the surface) — never a defense that doesn't exist, which would fake coverage
(BUILD-SPEC §5.2's own "no LARPing" rule). Concretely, a technique is in scope if it
targets one of:

1. A real `staleness_clocks` surface (`knowledge:*`, `fuzz-targets:first-built`,
   `environments:first-registered`, `fleet-enrollments:first-list`,
   `vuln_res:agent-registry-fallback`).
2. A real `capabilities` row (the 6 `vulnres-*` stage agents + orchestrator).
3. This portfolio's own build-time trust surface (`Cargo.lock`/`Cargo.toml`, vendored
   fixtures, CI guards).
4. The supervisor's own ingestion path (`tools/parsers.py`'s read sources) — in scope
   specifically because BUILD-SPEC §5.3's `agent-directed` profile names "this
   portfolio's own supervisor... is the attack surface" as a first-class concern, not
   speculative future scope.
5. A project 1-3 surface named in that project's own `PROPOSAL.md`, even though
   pre-build — "scheduled to have" per the rubric's own wording — but every such
   mapping's `verdict` honestly reflects pre-build status (`uncovered`, never
   `covered`).

Platform filter (A5): every mapped technique must have at least one
`technique_platforms` row intersecting `('macOS','Containers','IAAS','Linux')` — this
portfolio's real surfaces. A technique proposed for mapping with no matching platform
is rejected at ingest with a `parse_failures`-class row, never silently mapped anyway.

## Mapped subset (initial, this phase)

| Technique | Surface | Profile(s) that use it |
|---|---|---|
| T1195.001 | `knowledge:cargo-audit-clean`, `knowledge:build-test-clean` | opportunistic-supplychain |
| T1608.007 | supervisor ingestion path (`tools/parsers.py`) | agent-directed, opportunistic-supplychain |
| T1698 | supervisor ingestion path | agent-directed |
| T1699 | (no direct-prompt surface exists) | agent-directed — `not_applicable` by design |
| T1685.007 | `capabilities` (autonomous rows: disclosure/exploit-dev/triage) | agent-directed |
| T1021.004 | `fleet-enrollments:first-list` | patient-fleet |
| T1078 | `fleet-enrollments:first-list` | patient-fleet |
| T1222 | `vm_sec_research` / bputil-eval boot-security surface | patient-fleet (unattested preference, flagged) |

Each row's real `ttp_mappings` entry carries its `verdict`/`evidence_id`/`detect_via`
— this table is the human index, the database is authoritative.

## Re-pin procedure (A6)

Re-pinning (e.g. to v21) is **inserting** a new `attack_releases` row and re-running
`tools/ttp_ingest.py` against the new bundle — content rows are never UPDATEd after
ingest, so history stays queryable forever (every technique row carries its own
`release_id`). After ingest:

1. Run `db/queries/v_repin_diff` (a view, queried directly) — lists every
   new/revoked/changed technique that intersects an already-mapped surface.
2. That diff lands in the next brief as a needs-a-human item — never a silent content
   refresh (BUILD-SPEC §5.5's own rule).
3. Flip `attack_releases.is_pinned` to the new release only after the diff has been
   reviewed; the old release's rows stay in the DB, just no longer the pinned default
   for new mapping work.
