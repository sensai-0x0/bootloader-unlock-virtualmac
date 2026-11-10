# Ontology — object, link, and source→table mapping definitions (BUILD-SPEC §2.1)

Every object below is a table in `state/portfolio.db`; every claim a parser asserts
gets a `provenance` row pointing at the exact source path + anchor. Objects are
keyed by natural keys so re-ingest of the same unchanged source is a no-op, and a
changed source lands as new rows (append-only where the object is history: evidence,
milestone_log), not in-place edits.

## Objects

| Object | Table | Natural key | Ingest behavior on re-parse |
|---|---|---|---|
| **Initiative** | `initiatives` | `slug` | update-in-place of current state; the defining `proposal_ref` is the provenance anchor. Status is recorded with its inference basis until a real status file exists (`status_file_ref NULL`). |
| **Evidence** | `evidence` | `source_ref + content_hash` | append-only; a re-ingested identical source row dedupes (`UNIQUE`), a changed source adds a row. `kind` is one of the ten vuln_res-typed classes (parsed, not guessed). |
| **StalenessClock** | `staleness_clocks` *(phase 2)* | `surface` | never/counted; `NULL last_verified_at` is the first-class "never" fact. |
| **Finding** | `findings` *(phase 2)* | `source_ref` | append-only with dispute rows, never deletion. |
| **Environment** | `environments` *(phase 2)* | registry rows | read-only mirror, forever (§3.4). |
| **Milestone** | `milestones` | `(initiative_id, m_ref)` | verbatim from the source table; refs never renumbered/inserted (parser enforces the source file's own stated rules). |
| **Milestone log entry** | `milestone_log` | `(occurred_at, heading)` via `entry_key` hash | append-only; 'Next up' text is a decision-engine input. |
| **Link** | `links` | `(src_type, src_id, dst_type, dst_id, link_type)` | deduped by UNIQUE; weights re-derivable. |
| **Recommendation** | `recommendations` *(phase 3)* | `(score_run_id, rank)` | each score run is deterministic; identical inputs ⇒ identical rows. |
| **TTP / TechniqueSurface / SimScenario** | `ttps`, `ttp_mappings`, `sim_*` *(phase 5)* | `attack_id`, `(technique_id, surface)`, `scenario_id` | release-keyed (A6): re-pins insert, never update. |

## Vocabulary

### `initiatives.kind`
`project1_fuzz`, `project2_mutation`, `project3_drift`, `vulnres_suite`,
`supervisor`, `vm_sec_research`.

**Build-time amendment (§3.5 item 6, 2026-11-11, phase 1):** `vm_sec_research` is the
pre-`vuln_res/` bootloader-research program defined by `progress/goal.md` — the
program every M0–M10 in `progress/milestones.md` serves ("every milestone in
`milestones.md` is in service of goal.md"). The original five-kind enum gave those
milestones no owner, which would have forced either a wrong check constraint or
fragmented evidence. Owning the fact beats approximating it.

### `initiatives.status`
`pre-build`, `active`, `blocked`, `concluded`. Until a project publishes its own
phase-1 status file, the value is an **inference-with-provenance** (the provenance
row names the observation basis), never a fact.

### `evidence.kind`
Mirrors `vuln_res/knowledge/INDEX.md`'s own typing (environment / target-status /
general for knowledge entries; sweep summaries, findings, exploits and measurements
typed by the stores they come from): `knowledge`, `sweep_summary`, `finding`,
`exploit`, `milestone`, `measurement`, `rollup`, `environment_entry`, `fuzz_result`,
`commit_event`.

## Links

Links make the same real-world thing addressable together, without collapsing rows:

| link_type | from → to | meaning |
|---|---|---|
| `owns` | initiative → evidence | the evidence belongs to this initiative (FK-implied; materialized for query symmetry) |
| `bears-on` | milestone_log entry → milestone | a dated log entry "M8 started…" records events behind that milestone row |
| `concludes` | evidence → milestone | an evidence row (e.g. the log entry that says "Done", or a bundle path cited in the table) is the milestone's cited proof |
| `covers` | capability → initiative *(phase 2)* | the capability's trigger contract covers this initiative |
| `invalidates` | event → evidence/clock *(phase 2+)* | implication rule fired (§4.1) |

## Source→table mapping

Authority order and parser status live in `ontology/sources.yaml` (single registry,
added-to-first). Actor line per source: nothing here *executes*; parsing is reading
plus regex, period.

| Source (registry id) | Reads | Writes tables | Anchoring |
|---|---|---|---|
| `milestones` | `progress/milestones.md` status table + dated log; `progress/goal.md` | `milestones`, `milestone_log`, `evidence`(milestone), meta peg for the goal | milestone rows anchor to `#M-line`; log entries to `#<heading>`; goal peg to meta `portfolio_goal_sha256` |
| `knowledge` | `vuln_res/knowledge/INDEX.md` one-line entries + footer | `evidence`(knowledge; kind parsed from entry context + the file's own footer declarations) | entry anchor = `INDEX.md#-<slug>` |
| `sweep_reports` *(phase 2)* | sweep/finding indices, per-finding frontmatter | `sweeps`, `findings`, `exploits`, `evidence`(sweep_summary/finding/exploit) | per-file frontmatter |
| `environments_registry` *(phase 2)* | environments INDEX | `environments` | file rows |
| `project_lifecycle` *(phase 2)* | projects 01–03 PROPOSALs/status files | `initiatives` status + `status_file_ref` | per-file heading |
| `git_history` *(phase 2)* | `git log --name-only` | `events`, `evidence`(commit_event) | commit sha |
| `capability_registry` *(phase 2)* | `.claude/agents/*`, `.claude/skills/*/SKILL.md` | `capabilities` | file path |
| `attack_stix` *(phase 5)* | pinned release bundle | `attack_releases`, `tactics`, `techniques`, joins, `technique_revisions` | STIX id + release tag |

## Parser contracts

1. Parse failures are first-class: a failing source emits `parse_failures` (with
   provenance naming the failing file) and degrades to authority 0 **for that run**.
   Never guess through.
2. "Newer dated entries outrank older ones, and nothing else does" — the resolution
   rule for `milestones`-source disputes (same-file recency wins; cross-source
   disputes go through authority order into `contradictions`).
3. Milestone refs are append-only (`M<n>` strictly increases). A source that
   renumbers or inserts is a semantic parse failure.
4. Knowledge entry kind is parsed data: an entry is `environment`/`target-status`
   only when the INDEX's own footer declares such entries exist; everything else is
   `general`. A footer claiming entries that aren't listed (or vice versa) is a
   parse failure, not a silent reconciliation.
