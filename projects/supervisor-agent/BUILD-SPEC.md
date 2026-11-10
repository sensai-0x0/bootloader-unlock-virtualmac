# Supervisor agent — build spec ("Portfolio Supervisor", codename `supervizor`)

**Status:** executable build spec, expanded from `PROPOSAL.md` (read that first — it is
the contract this spec implements; nothing here widens it).
**Audience:** a building agent. Execute phases in order. Do not start a phase before the
previous phase's acceptance test passes and its evidence is recorded.
**Hard rule that governs every line below:** the supervisor reads, computes, models, and
recommends. It never executes. Every verb outside `read/parse/diff/score/rank/model/
write supervisor-state/dispatch-with-approval` is somebody else's job — and that stays
true for the TTP simulation layer too: adversaries are simulated as *decision models and
gap probes*, never as tooling that runs anything.

---

## 0. What "Palantir-like power" means here (and what it does not mean)

The power is **fusion**, not authority. Palantir's actual edge was never privileged
access — it was: (1) a shared ontology so every source maps to the same objects, (2)
provenance on every fact, (3) entity resolution across heterogeneous stores, (4) a
timeline view so analyst attention goes to what changed *and what it implicates*, and
(5) a decision brief that turns all of that into one ranked "what next". This spec
builds exactly those five things over this portfolio's own data, with one addition
Palantir analysts did manually and we make computational: **a standing adversary model
(MITRE ATT&CK) that is used to stress the fused picture for blind seams**. The
supervisor gets:

- **Ontology** — one shared object model spanning `vuln_res/` sweeps, `progress/`
  milestones, projects 1–3 status, the environment registry, git history, and now the
  ATT&CK technique corpus.
- **Provenance** — every fact it asserts carries a source path + timestamp + how it was
  derived. Golden rule 8 (honesty of state) applied to the supervisor's own outputs —
  and now enforced structurally, since every row in the database carries provenance.
- **Entity resolution** — the same real-world thing appearing in three stores (a finding
  in `sweep-reports/`, a knowledge entry, a milestone log line) resolves to one object,
  not three fragments.
- **Implication/timeline analysis** — "a `Cargo.lock` change landed => every staleness
  claim about dependency audit is now suspect" computed, not guessed.
- **Decision briefs** — a ranked, scored, provenance-backed recommendation of the next
  unit of work, which still requires a human to pull the trigger on anything that
  executes.
- **TTP-grounded red-teaming of itself** — an ATT&CK-mapped adversary decision model
  (§5) that simulates *how a patient adversary would sequence their program against
  surfaces this portfolio is supposed to defend*, and uses the fused state to answer:
  "if the adversary did X, would anything here have noticed, how fast, and through
  which capability?" The simulation runs entirely inside the model; it never generates
  or executes attack tooling. It outputs gap probes, coverage verdicts, and
  recommendations — the same outputs everything else in this supervisor produces.

What it never gets: any command channel (`wrapper.rs`, `cargo fuzz`, `tart`, SSH), any
environment registration, any scheduling/cron authority, any write outside its own state
directory. Rich analysis and adversarial modeling, zero execution surface.

---

## 1. Deliverables (complete file inventory)

```
projects/supervisor-agent/
├── PROPOSAL.md                      (exists)
├── BUILD-SPEC.md                    (this file)
├── ontology/
│   ├── SCHEMA.md                    object/link definitions + source→table mapping rules
│   └── sources.yaml                 source registry (§2) — paths, parsers, authority order
├── db/
│   ├── schema.sql                   the whole database, versioned as code (§3)
│   ├── migrations/                  NN-description.sql, applied in order, never edited
│   └── queries/                     named, reviewed SQL used by every brief table (§4)
├── ttp/
│   ├── LIBRARY.md                   the pinned ATT&CK subset + adversary decision model (§5)
│   ├── mappings.yaml                technique → check-surface → capability mapping
│   └── profiles/                    one .md per simulated adversary profile (§5.3)
├── state/
│   ├── portfolio.db                 THE fused database (§3) — the supervisor's main store
│   ├── fused-portfolio.md           generated VIEW of the DB for human reading (regenerated)
│   └── decision-log.md              human-readable mirror of the decision_log table
├── briefs/                          generated decision briefs (YYYY-MM-DD-NNN-brief.md)
├── tools/
│   └── supervisor.py                the runner: init/audit/provenance-null/mirror/decide,
│                                    growing one command per phase
├── tests/
│   ├── SCENARIOS.md                 dry-run evaluation scenarios (§8)
│   └── self-audit.md                the invariant checklist, run every session start
└── README.md                        how to run, the escalation ladder, runbook
```

The markdown files under `state/` and everything in `briefs/` are **generated output** —
always rebuild-able from `portfolio.db`. The database is the single source of truth;
markdown remains the human interface, matching how every other store in this repo is
read (grep/diff), without making markdown the machine authority anymore. If a `.md`
mirror and the database disagree, the database wins and the mirror is regenerated;
disagreement itself is recorded (§3, `sync_violations`).

---

## 2. Ontology & source registry (`ontology/sources.yaml`)

### 2.1 Object types (unchanged from the original spec, now as tables)

| Object | Defined by | Key properties |
|---|---|---|
| **Initiative** | a project or sweep program (project 1/2/3, `vuln_res/` itself) | status, phase-coverage, last-activity, owner-gate type |
| **Evidence** | any recorded measurement/finding/report | source path, hash-if-committed, verdict class, links to exactly one Initiative |
| **Capability** | a dispatchable unit of work (any `vulnres-*` agent/skill) | trigger contract, approval class (autonomous / user-gated / gated+1TR) |
| **StalenessClock** | one thing that decays | id, last-verified timestamp, invalidating-events, decay policy |
| **Finding** | triaged vuln_res finding | rubric score, disposition, resolution point |
| **Environment** | registry entry | status, approved_for — read-only mirror |
| **Recommendation** | one decision-brief line | target, score components, required gate, provenance |
| **TTP** *(new)* | one ATT&CK technique (or sub-technique), normalized per §3.1/§3.3 | attack_id, name, tactic(s) via join, platform(s) via join, pin/release, revision history |
| **TechniqueSurface** *(new)* | the defensive-check surface a TTP exercises on THIS portfolio | what would detect/limit it, which Capability covers it, verdict |
| **SimScenario** *(new)* | one simulated adversary decision-sequence | profile, phase vector, TTP steps, gap probes raised |

### 2.2 Sources (all verified present today; parsers are read-and-regex over documented formats)

1. `progress/goal.md`, `progress/milestones.md` → Initiative, Evidence. Authority: high
   (the user's own record; newer dated entries in the same file outrank older ones and
   nothing else does).
2. `vuln_res/knowledge/INDEX.md` (+ linked files) → Evidence, StalenessClock anchors.
   Authority: medium. Parse the documented one-line-plus-`(updated: …)` format.
3. `vuln_res/sweep-reports/INDEX.md`, `findings-index.md`, per-finding frontmatter →
   Finding, Evidence. Authority: medium-high (findings with committed evidence
   outrank prose claims).
4. `vuln_res/knowledge/environments/INDEX.md` → Environment, read-only mirror forever.
5. `projects/{01,02,03}-*/PROPOSAL.md`, later each project's phase-1 status file →
   Initiative lifecycle. Status file absent ⇒ phase = pre-build, recorded as
   *inference-with-provenance*, not fact.
6. `git log --since=… --name-only` (read-only) → Event stream for implication analysis.
   File-level at Phase 2; content-aware joins at Phase 4.
7. `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` → Capability + each one's
   documented approval class.
8. **ATT&CK STIX bundle (pinned)** — *(new, Phase 5)* the release-tagged STIX bundle from
   the `mitre/cti` GitHub release `ATT&CK-v20.1` (October 2026, current at spec time;
   re-pin and record the actual hash at build time). Feeds the `ttps` table. The pin is
   explicit: ingest the version that was downloaded, record its URL + hash + release tag
   in `db` meta, and re-pinning is a new build-time decision, never a silent refresh.

If a source fails to parse, emit a `parse_failures` row (first-class, with provenance)
and degrade that source's authority to zero for the run. Never guess through a parse
failure — report honestly, matching how `vuln_res` treats unparseable state.

---

## 3. Storage: the fused database (`state/portfolio.db`)

SQLite, one file, WAL mode, all DDL in `db/schema.sql`, every change through a numbered
migration file in `db/migrations/` (append-only, never edit an applied migration).

### 3.1 Schema (planned tables)

**Meta / provenance backbone** — provenance is structural, per-row, not a separate log:

```sql
-- every substantive row inherits these two columns:
--   provenance_id   REFERENCES provenance(id)
--   ingested_at     TEXT (ISO-8601, UTC)

provenance (
    id INTEGER PRIMARY KEY,
    source_ref   TEXT NOT NULL,   -- file path + anchor (file.md#heading or file:line)
    source_sha   TEXT,            -- blob hash when the source is committed content
    source_type  TEXT NOT NULL,   -- registry id from ontology/sources.yaml
    derived_from BLOB,            -- JSON: which upstream rows/queries produced this
    note         TEXT
)

runs (
    id INTEGER PRIMARY KEY, started_at TEXT, ended_at TEXT,
    trigger TEXT, sources_parsed TEXT, degraded_sources TEXT,
    db_version INTEGER, schema_hash TEXT, outcome TEXT
)

meta (key TEXT PRIMARY KEY, value TEXT)   -- pinned ATT&CK release tag/URL/hash, etc.

sync_violations (          -- md mirror disagrees with db; database wins, violation logged
    id INTEGER PRIMARY KEY, mirror_path TEXT, check_ran_at TEXT, detail TEXT
)
```

**Core fused state:**

```sql
-- ─── core fused state ────────────────────────────────────────────────────────
initiatives (id, slug, name, kind CHECK (kind IN
                ('project1_fuzz','project2_mutation','project3_drift','vulnres_suite','supervisor')),
              status, phase_coverage TEXT, owner_gate TEXT,
              proposal_ref TEXT,                 -- path to the PROPOSAL.md that defines it
              status_file_ref TEXT NULL)         -- NULL until the project's phase-1 file exists
evidence    (id, initiative_id, kind CHECK (kind IN
                ('knowledge','sweep_summary','finding','exploit','milestone','measurement',
                 'rollup','environment_entry','fuzz_result','commit_event'),
              verdict_class TEXT, content_hash TEXT, source_ref TEXT NOT NULL, …)
              -- kind mirrors how vuln_res/knowledge/INDEX.md types its own entries
              -- (environment / target-status / general) so typing is parsed data, not guesswork
findings    (id, sweep_id, initiative_id, rubric_score, disposition,
              resolution_ref, provenance_id, …)
exploits    (id, finding_id REFERENCES findings(id),
              outcome_class CHECK (outcome_class IN ('our_code','upstream','escalate')),
              artifact_ref TEXT, provenance_id …)
              -- the vulnres-disclosure three-outcome model, as data

-- ─── the vuln_res suite, first-class ─────────────────────────────────────────
sweeps      (id, initiative_id, kind CHECK (kind IN
                ('recon','fuzz_harness','environment_run','triage','exploit_dev',
                 'disclosure','full_orchestrated')),
              report_dir TEXT,                   -- sweep-reports/<id>/ path
              started_at, closed_at, outcome TEXT,
              agents_invoked TEXT,               -- JSON list; proves orchestrator shape
              provenance_id …)
capabilities(id, name, agent_or_skill, kind CHECK (kind IN
                ('agent','skill','project_runner','supervisor')),
              suite INTEGER NOT NULL REFERENCES initiatives(id),
              approval_class CHECK (approval_class IN
                ('autonomous','user_gated','gated_plus_1tr')),
              trigger_contract TEXT, provenance_id …)
environments(id, status, approved_for, lifecycle, provider, provenance_id …)
              -- read-only mirror of knowledge/environments/INDEX.md, forever (its SCHEMA.md
              -- fields verbatim); the supervisor's only relationship to this table is reading
fuzz_targets(id, initiative_id, name, target_path TEXT, harness_ref TEXT,
              seed_corpus_ref TEXT, last_run_at TEXT, last_result TEXT, provenance_id …)
              -- fed by target-status knowledge entries; NULL last_run_at is the honest
              -- "never fuzzed" fact that project 1's Phase acceptance tests lean on

-- ─── portfolio tracking ─────────────────────────────────────────────────────
milestones  (id, initiative_id, m_ref TEXT NOT NULL,     -- 'M8' …
              title TEXT, status TEXT,                   -- verbatim from the table row
              evidence_ref TEXT, updated_at TEXT,
              UNIQUE(initiative_id, m_ref))              -- invariant: never renumbered/inserted
milestone_log(id, initiative_id, occurred_at TEXT NOT NULL,-- the dated entries BEHIND the
              m_refs_touched TEXT, detail TEXT,           -- table; 'Next up' lines here are
              next_up TEXT, provenance_id …)              -- a decision-engine input, not prose
cadence_reports(id, initiative_id, cadence CHECK (cadence IN ('daily','weekly','monthly')),
              path TEXT NOT NULL, created_at TEXT, provenance_id …)
              -- vulnres-reporting output trails; staleness_clocks may key on this table's
              -- max(created_at) per cadence, so a missed weekly rollup decays like any clock
fleet_enrollments(id, initiative_id, hostname TEXT UNIQUE,
              enrolled_at TEXT, enrolled_by TEXT CHECK (enrolled_by = 'user'),
              baseline_ref TEXT, last_eval_at TEXT, last_eval_state TEXT, provenance_id …)
              -- project 3's explicit, hand-maintained list; 'user'-only CHECK builds the
              -- no-auto-discovery rule into the schema itself
schedules   (id, capability_id …, cadence TEXT,
              approval_status CHECK (approval_status IN ('proposed','approved','retired')),
              approved_by TEXT NULL, approved_at TEXT NULL, provenance_id …)
              -- when the user ever approves a standing cadence, it becomes a row here —
              -- never a cron side-effect; 'proposed' rows are brief text and nothing else

-- ─── staleness / implication / ranking ──────────────────────────────────────
staleness_clocks(id, capability_id …, initiative_id …, surface TEXT,
                 last_verified_at TEXT NULL,          -- NULL = 'never', first-class (§4)
                 last_verified_by INTEGER REFERENCES evidence(id),
                 invalidates_on TEXT, policy TEXT,
                 state CHECK (state IN ('live','invalid','never','missing_evidence')))
events      (id, kind, occurred_at, detail, provenance_id …)
clock_invalidation_events (clock_id …, event_id …, fired_at)
implications  (event_id …, effect_kind, effect_ref, rule_id …)
contradictions(id, losing_evidence_id …, winning_evidence_id …, detected_at, detail)
links       (src_type, src_id, dst_type, dst_id, link_type, weight, provenance_id …)
score_runs  (id, computed_at, inputs_hash UNIQUE)
recommendations (score_run_id …, rank, initiative_id …, capability_id …,
              score_total, score_staleness, score_blast, score_readiness, score_precedent,
              required_gate TEXT, brief_id …)

-- ─── supervisor self-governance ─────────────────────────────────────────────
audit_runs  (id, run_id …, checklist_version TEXT, passed INTEGER,
              violations TEXT, at TEXT)
              -- §7's self-audit records EVERY run, pass and fail — a silent pass is
              -- as unpublishable as a loud fail
sync_violations(id, mirror_path, check_ran_at, detail)
parse_failures(id, source_ref, at, detail)
briefs      (id, path, created_at, run_id …, do_next_top3 TEXT, needs_human TEXT)
dispatch_tickets(id, brief_id …, capability_id …, scope_invariants TEXT,
              required_gate TEXT, approval_status DEFAULT 'pending',
              approved_by TEXT NULL, approved_at TEXT NULL, executed_at TEXT NULL)
decision_log(id, at, kind, brief_id NULL, ticket_id NULL, outcome, detail)
runs        (id, started_at, ended_at, trigger, sources_parsed TEXT,
              degraded_sources TEXT, db_version INTEGER, schema_hash TEXT, outcome TEXT)
meta        (key TEXT PRIMARY KEY, value TEXT)
```

**Implication & ranking:**

```sql
clock_invalidation_events (clock_id, event_id, fired_at)   -- §3.2's computed history
implications  (event_id, effect_kind, effect_ref, rule_id) -- event → affected rows
score_runs    (id, computed_at, inputs_hash)               -- determinism anchors
recommendations(score_run_id, rank, initiative_id, capability_id,
                score_total, score_staleness, score_blast, score_readiness,
                score_precedent, required_gate, brief_id)
```

**TTP layer (Phase 5):**

The ATT&CK layer is normalized, not a flat dump — every table below exists to make a
specific analytics question a reviewed JOIN (see §3.3 for the requirement→table map):

```sql
-- Releases: re-pinning is inserting a row, never updating content in place (A6)
attack_releases (
    id INTEGER PRIMARY KEY, tag TEXT UNIQUE,      -- e.g. 'ATT&CK-v20.1'
    released_at TEXT, bundle_url TEXT, bundle_sha256 TEXT UNIQUE,
    is_pinned INTEGER NOT NULL DEFAULT 0, ingested_at TEXT
) -- CHECK: at most one is_pinned = 1

tactics (
    id INTEGER PRIMARY KEY, attack_id TEXT UNIQUE,  -- e.g. 'TA0007'
    name TEXT, short_name TEXT                      -- short_name drives phase joins
)

techniques (
    id INTEGER PRIMARY KEY,
    attack_id TEXT UNIQUE,                          -- 'T1608', 'T1608/007'
    name TEXT NOT NULL,
    is_subtechnique INTEGER NOT NULL DEFAULT 0,
    parent_attack_id TEXT,                          -- self-join for base rollup (A3)
    description TEXT,
    revoked INTEGER DEFAULT 0, deprecated INTEGER DEFAULT 0,
    release_id INTEGER NOT NULL REFERENCES attack_releases(id)
)
CREATE UNIQUE INDEX idx_tech_attack_id ON techniques(attack_id);
CREATE INDEX idx_tech_parent ON techniques(parent_attack_id);

-- version history per technique: diffing v20.1 → v21 = comparing rows, not updating (A6)
technique_revisions (
    id INTEGER PRIMARY KEY, technique_attack_id TEXT NOT NULL,
    release_id INTEGER NOT NULL REFERENCES attack_releases(id),
    version TEXT NOT NULL, revision_note TEXT,
    UNIQUE(technique_attack_id, release_id)
)

-- multi-valued facets: a technique maps to SEVERAL tactics and platforms (A1, A5)
technique_tactics   (technique_id … REFERENCES techniques(id),
                      tactic_id … REFERENCES tactics(id), UNIQUE(technique_id, tactic_id))
technique_platforms (technique_id …, platform TEXT, UNIQUE(technique_id, platform))
technique_groups    (technique_id …, group_attack_id TEXT, group_name TEXT,
                      source_ref TEXT,   -- STIX relationship id, in release
                      UNIQUE(technique_id, group_attack_id, source_ref))
technique_campaigns (technique_id …, campaign_attack_id TEXT, campaign_name TEXT,
                      source_ref TEXT, UNIQUE(technique_id, campaign_attack_id))
technique_detcount  (technique_id …, release_id …, det_strategies INTEGER,
                      analytics INTEGER)   -- v20 counts = prior-art signal for detect_via

-- mapping of techniques to THIS portfolio's check surfaces — the analytics heart
ttp_mappings (
    id INTEGER PRIMARY KEY, technique_id NOT NULL REFERENCES techniques(id),
    surface TEXT NOT NULL,          -- e.g. 'enrolled-fleet-ssh', 'Cargo.lock-provenance'
    capability_id INTEGER REFERENCES capabilities(id),
    detect_via TEXT, limit_via TEXT,
    verdict TEXT NOT NULL CHECK (verdict IN
        ('covered','partially_covered','uncovered','asserted_unproven','not_applicable')),
    evidence_id INTEGER REFERENCES evidence(id),   -- NULL ⇒ verdict MUST be asserted_unproven
    provenance_id INTEGER NOT NULL REFERENCES provenance(id),
    UNIQUE(technique_id, surface)
)
CREATE INDEX idx_map_capability ON ttp_mappings(capability_id);

-- portfolio phases: which tactics belong to which standing-program phase (A1)
phase_tactics (id INTEGER PRIMARY KEY, phase TEXT NOT NULL,
               tactic_attack_id TEXT NOT NULL REFERENCES tactics(attack_id), UNIQUE(phase, tactic_attack_id))
-- REVIEWED DATA, e.g. init/recon ← Reconnaissance, Resource Development;
-- persist/expand ← Persistence, Priv Esc, Defense Evasion, Discovery, Lateral Movement;
-- execute ← Initial Access, Execution; triage-learn ← Collection, Credential Access, Exfiltration;
-- persist/report ← Command & Control, Impact, and C2-over-logs detection.

-- adversary profiles and the simulated decision loop (A4: candidates pull from real usage)
tp_profiles    (id, name UNIQUE, description, skill_level, patience,
                phase_vector TEXT, notes, provenance_id …)
sim_scenarios  (id, profile_id …, seed INTEGER NOT NULL,
                phase_sequence TEXT, release_id … REFERENCES attack_releases(id),
                created_at, run_id …)
sim_steps      (id, scenario_id, seq, technique_id … REFERENCES techniques(id),
                intent TEXT, success_predicted INTEGER, basis TEXT,   -- basis = provenance
                UNIQUE(scenario_id, seq))
sim_gaps       (id, scenario_id …, step_id … REFERENCES sim_steps(id),
                gap_kind TEXT, question TEXT, verdict TEXT, raised_into_brief INTEGER,
                recommendation_id INTEGER NULL REFERENCES recommendations(id))
sim_outcomes   (id, scenario_id … UNIQUE, summary TEXT,
                top_gap_ids TEXT, coverage_by_phase TEXT)
```

Indexes exist on every FK the ranking and gap-probe queries join through (capability,
surface, technique, step) — the acceptance queries in `db/queries/` are required to
EXPLAIN as index-driven, not table scans, once the mapped-subset size warrants it.

**Human outputs:**

```sql
briefs    (id, path, created_at, run_id, do_next_top3 TEXT, needs_human TEXT)
dispatch_tickets(id, brief_id, capability_id, scope_invariants TEXT,
                 required_gate, approval_status DEFAULT 'pending',
                 approved_by TEXT NULL, approved_at TEXT NULL, executed_at TEXT NULL)
decision_log(id, at, kind, brief_id NULL, ticket_id NULL, outcome, detail)
```

### 3.2 Rules for the database

- **The supervisor's ONLY writable area** is `state/`, `briefs/`, `db/` additions, and
  `ttp/` — grep-provable every run (§7).
- Provenance on every row, nullable never: a row with no source is a build bug, and
  `self-audit` includes the query `SELECT count(*) FROM <every table> WHERE
  provenance_id IS NULL` = 0.
- **No facts are deleted.** Corrections happen by adding a contradicting evidence row
  and letting the `contradicts` resolution rule mark the loser, preserving history —
  the same "we thought X, then found Y" principle `progress/milestones.md` already
  states for its own log.
- Determinism anchors: each scoring run stores its `inputs_hash`; identical inputs
  must produce byte-identical ranking (§4 acceptance).
- All analysis SQL used by briefs lives in reviewed files under `db/queries/` — briefs
  never inline ad-hoc SQL, so every analytical claim is traceable to a reviewed query,
  and regressions are diffable as query diffs.
- Sync rule: `fused-portfolio.md` and `decision-log.md` are regenerated from the DB at
  the end of every run; regenerate-then-diff, log any mismatch to `sync_violations`.

### 3.3 Technique-layer analytics requirements → schema decisions (the "why" for §3.1)

1. **Phase-coverage per technique (A1).** A technique can serve several tactics
   (ATT&CK's own intersection rows: e.g. valid accounts under multiple tactics), so a
   `tactic` *column* on `techniques` is wrong by construction. (`technique_tactics`
   join + reviewed `phase_tactics` table + `CREATE VIEW v_technique_phase AS SELECT
   t.*, pt.phase FROM techniques t JOIN technique_tactics tt … JOIN phase_tactics pt …`
   — phase becomes data, reviewable in diffs, changeable without touching code.)
2. **Latency-ranked gap probes (A2).** The brief's top-gap ranking is
   `techniques → ttp_mappings.surface → capabilities → staleness_clocks.state` as one
   reviewed query in `db/queries/`. Hence `ttp_mappings.capability_id` is a real FK,
   and `evidence_id` sits in the mapping itself: a `covered` verdict with `NULL`
   evidence is *structurally impossible* (`CHECK`-adjacent rule enforced at load time:
   NULL evidence forces `asserted_unproven`), which is §5.5's self-check requirement
   turned into schema rather than procedure.
3. **Sub-technique rollup (A3).** Coverage of `T1608/007` implies base-level coverage
   of `T1608` — rollup happens through `parent_attack_id` in a view
   (`v_coverage_rollup`), so per-base-technique counts in briefs never double-count a
   mapped sub-technique.
4. **Profile grounding (A4).** `technique_groups`/`technique_campaigns` make "which
   techniques did Salt Typhoon / G1045-class actors actually use, in v20" a query, so
   sim candidate selection (§5.4) is seeded by attested usage + `phase_tactics`
   filtering — profile authors reference group IDs, the DB does fact-finding. A
   profile preferring techniques no attested group uses must say why in its file, or
   the sim log records `unattested_preference` as a caveat row.
5. **Platform relevance (A5).** `technique_platforms` exists because the portfolio's
   surfaces are macOS + container: queries filter to `platform IN ('macOS','Containers',
   'IAAS','Linux')`, and any mapping proposed for a technique with no matching platform
   is rejected at ingest with a `parse_failures`-class row.
6. **Re-pin as diff, not mutation (A6).** All ATT&CK content rows are keyed to
   `attack_releases`; re-pinning v21 inserts rows and runs the reviewed diff query
   (`v_repin_diff`: new/revoked/major-changed techniques *intersecting already-mapped
   surfaces*) whose output lands in the brief as a needs-human item. Content rows are
   never UPDATEd after ingest — history stays queryable forever.
7. **Detection prior art (A7).** `technique_detcount` (v20: 703 Enterprise detection
   strategies / 1770 analytics) lets mappings record, next to `detect_via`, that MITRE
   itself documents *n* strategies for the technique — a technique with detcount 0 that
   we claim `covered` for is flagged for extra scrutiny in the self-check, because the
   community found no detection before us.

### 3.4 Suite completeness map — every repo entity family must have an owning table

The schema is complete only when every artifact family this portfolio actually produces
maps to a table, a clock, or a deliberately-absent-with-reason row. Building agents run
the accounting query (`SELECT name, (SELECT count(*) FROM …)` across all tables, from
`db/queries/accounting.sql`) at every phase boundary; any family in the map below
without its table, or any table with no entry in this map, is a spec violation.

| Repo entity family | Where it lives today | Owning table(s) | Clocks it can feed |
|---|---|---|---|
| The 6 vulnres stage agent definitions | `.claude/agents/vulnres-*.md` | `capabilities` (kind=agent, suite→vulnres_suite) | via capability coverage |
| vulnres-orchestrator | `.claude/agents/vulnres-orchestrator.md` | `capabilities` | — |
| vulnres-reporting, -pattern-analysis | `.claude/skills/*/SKILL.md` | `capabilities` (kind=skill) | `cadence_reports` max(created_at) |
| Sweep programs run so far | `vuln_res/sweep-reports/<id>/` + INDEX.md | `sweeps`, `evidence` (kind=sweep_summary) | never-run-kind sweeps surface as `never` clocks |
| Individual findings | `sweep-reports/<id>/<finding>.md`, findings-index | `findings` (FK sweep_id), `evidence` (kind=finding) | resolved-finding staleness |
| Weaponized/developed exploits | `sweep-reports/exploits-index.md` | `exploits` (outcome_class per disclosure model) | open-exploit aging |
| Durable knowledge entries | `vuln_res/knowledge/INDEX.md` (+linked) | `evidence` (kind parsed from entry type) | assertions keyed in INDEX timestamps |
| Environment registry | `knowledge/environments/INDEX.md` | `environments` (read-only) | zero-rows ⇒ execute-phase blocked fact |
| Milestone status | `progress/milestones.md` table | `milestones` | milestone aging (in-progress rows) |
| Milestone dated log ('Next up') | `progress/milestones.md` log section | `milestone_log` | drives do-next directly |
| Portfolio goal | `progress/goal.md` | `initiatives` (or `meta` peg + evidence) | — |
| Projects 1–3 definitions | `projects/{01,02,03}-*/PROPOSAL.md` | `initiatives` (proposal_ref; status_file_ref NULL until theirs exist) | per-initiative last-activity |
| Fuzz targets (when built) | project 1 artifacts + target-status entries | `fuzz_targets` | last_run_at decay |
| Fleet enrollment list (project 3) | project 3's hand-maintained file | `fleet_enrollments` | last_eval_at decay |
| Cadence rollups | `reports/{daily,weekly,monthly}/` | `cadence_reports` | cadence decay |
| Opaque units of work | each PROPOSAL's dispatch targets | `capabilities` (kind=project_runner) | — |
| Approved standing schedules | the PROPOSAL's "never a cron entry" rule | `schedules` (approval_status=row-changed by user only) | — |
| The supervisor's own outputs | `state/`, `briefs/`, `db/` | `runs`, `briefs`, `dispatch_tickets`, `decision_log`, `audit_runs`, `sync_violations` | self-audit freshness |
| The supervisor's own definitions | `PROPOSAL.md`, `BUILD-SPEC.md`, `README.md` | `meta` pegs + `provenance` refs | spec-version drift check |

---

### 3.5 Build-time amendments (appended as phases execute; each dated)

The spec is contract, but executing it surfaced real ambiguities. Fixes are recorded
here rather than silently resolved in code — every entry cites the phase that earned it.

1. *(phase 0, 2026-11-11)* **`schema.sql` vs. migrations.** `db/schema.sql` is the
   cumulative idempotent DDL snapshot (one file, current truth, versioned as code);
   `db/migrations/NNNN-*.sql` record each change from the previous phase's snapshot,
   applied in filename order, never edited after apply. Both use `IF NOT EXISTS`, so
   applying the snapshot and replaying migrations is idempotent by construction. The
   applied-migrations ledger lives in `meta` (`applied_migrations`, JSON array, applied
   order); `db_version` = the highest applied migration number.
2. *(phase 0, 2026-11-11)* **`audit_runs` ships with phase 0** (migration
   `0001-add-audit-runs.sql`), although phase 0's table list said
   "meta/provenance/runs/decision_log only". §7 requires recording every self-audit
   run — "a silent pass is as unpublishable as a loud fail" — and the very first audit
   is part of phase-0 acceptance, so a judgment-call-free gate needs its own table
   from the start.
3. *(phase 0, 2026-11-11)* **Provenance-null audit scope.** The §7 invariant-2 check
   runs over every table that carries a `provenance_id` column. The four
   self-governance tables (`meta`, `runs`, `decision_log`, `audit_runs`) are exempt
   by construction: each row's provenance IS the run that wrote it (the
   `brief_id`/`ticket_id` columns keep them anchored to run context).
4. *(phase 0, 2026-11-11)* **Store hygiene.** `state/portfolio.db` is committed (the
   database is the source of truth and its history should be diffable in git); the WAL
   is checkpointed (`PRAGMA wal_checkpoint(TRUNCATE)`) after every write, and the
   `-wal`/`-shm` sidecars are gitignored — no binary sidecar land ever.
5. *(phase 0, 2026-11-11)* **Mirror granularity.** `state/decision-log.md` is
   regenerated by the runner after every `decision_log` write (`mirror` command plus
   post-write hooks), not merely at end-of-run — invariant 9 enforced at
   command granularity, so drift can only be transient, never persisted.
6. *(phase 1, 2026-11-11)* **`initiatives.kind` gains `vm_sec_research`**
   (migration `0002`). The original five kinds
   (`project1_fuzz/project2_mutation/project3_drift/vulnres_suite/supervisor`) give
   `progress/milestones.md`'s M0–M10 no owner: §3.4's map says milestone rows live in
   `milestones` (FK to initiatives), and the acceptance test requires M8–M10 to
   resolve to ONE initiative — but those milestones serve the pre-`vuln_res/`
   bootloader-research program defined by `progress/goal.md`
   ("every milestone here exists in service of goal.md" — milestones.md header).
   Forcing them under a wrong kind would fragment the evidence chain the acceptance
   test forbids. The honest schema row wins over the tidy enum; §3.1's CHECK is
   amended accordingly.
7. *(phase 1, 2026-11-11)* **Milestone-anchoring rule.** Milestone rows anchor to the
   initiative whose goal statement they serve (`progress/goal.md` →
   `vm_sec_research` today). A future initiative that publishes its own milestone
   section must register its anchor range in `ontology/sources.yaml`'s
   `milestone_anchors` before the parser will bind rows for it — no implicit claim.
8. *(phase 1, 2026-11-11)* **Parse test fixtures are honest artifacts.** The
   parse-failure acceptance test ships a deliberately mangled fixture under
   `tests/fixtures/`, produced by the parser's `--self-test` mode; the fixture is
   flagged in its own first line as a test artifact, so the DB never confuses it
   with real portfolio state.
9. *(phase 1, 2026-11-11)* **A4's grep scope.** The forbidden-pattern grep targets
   the supervisor's *own* analysis output (`briefs/`, `state/decision-log.md`),
   not the mirrors of user-authored sources. `state/fused-portfolio.md` is exempt:
   it faithfully quotes `progress/milestones.md`, whose real log lines describe
   pre-`vuln_res/` VM-boot SSH/tart history. Quoting the user's record verbatim is
   the spec (§1 "markdown remains the human interface"); flagging it would make
   the audit fail on honest fusion.
10. *(phase 2, 2026-11-11)* **Snapshot-first means snapshot-complete.** The
   snapshot-first rule (item 1 applied to fresh rebuilds: a fresh DB takes its
   ledger from the snapshot without replaying migrations) failed its first
   honest test — `audit_runs` (migration 0001) was missing from `schema.sql`,
   so a rebuild produced a ledger claiming `0001` applied with no table to
   show for it. Rebuilt the state DB from the corrected snapshot; the rule is
   "the snapshot must contain every migration's DDL", re-verified after every
   migration by rebuilding a scratch DB and diffing `.tables`.
11. *(phase 2, 2026-11-11)* **R1 invalidation granularity = local date.**
   §4.1's "event postdates the claim" was underspecified against the data: git
   event strings carry their own UTC offset, while claim anchors are date-only
   local strings. Under raw string comparison a same-day commit that *created*
   the asserted claim invalidates it — a false positive, since the anchor
   describes exactly that day's state. Rule R1 v2 (`r1-event-invalidates-clock.sql`)
   compares at local-date granularity (an anchor `2026-11-10` survives events
   dated `2026-11-10` in any offset; strict later days invalidate) and falls
   back to `claim_anchors.asserted_at` when `last_verified_at` is NULL — its
   own comment had promised that join. Content-level same-day contradictions
   stay R2's job; R2's verdicts were unaffected.
12. *(phase 2, 2026-11-11)* **Synthetic events use the git timestamp format.**
   `event synthetic` writes `occurred_at` with the local UTC offset
   (`+HH:MM`), matching parsed git strings, so R1's local-date comparison
   treats described events exactly like real ones — the acceptance
   demonstration (Cargo.lock ⇒ `cargo-audit-clean` flips) fires on the same
   rule path a real commit would, with no special-casing in SQL.
13. *(phase 3, 2026-11-11)* **SQLite has no `(VALUES …) AS alias(col)`
   derived-table syntax.** `v_phase_coverage`'s phase enumeration
   (`CROSS JOIN (VALUES ('recon'), …) AS ph(phase)`) is valid standard SQL
   but not valid SQLite — confirmed against sqlite3 3.54.1, which accepts
   the equivalent `WITH alias(col) AS (VALUES …)` CTE form but rejects the
   same column-alias list on an inline derived table. Rewritten as
   `(SELECT 'recon' AS phase UNION ALL SELECT 'build' …) AS ph`, re-verified
   by rebuilding a scratch DB from `schema.sql` alone and diffing `.tables`
   (§3.5 item 10's own rule, re-applied).
14. *(phase 3, 2026-11-11)* **`v_score_inputs` is the canonical, exhaustive
   input set — nothing q-scoring.sql doesn't consume.** Factors: 4 clock
   states (`clock_live/invalid/never/missing`), 2 capability-approval
   buckets (`cap_autonomous/cap_gated`), 2 finding stats
   (`finding_count/finding_avg_score`), 1 global readiness gate
   (`environments_registered`) — 9 factors × 6 initiatives, zeros included.
   A `milestones_open` factor was drafted then removed before the first real
   `score` run: the view's own header says "EVERY factor row the rubric
   consumes," and nothing in q-scoring.sql read it — an unused factor would
   widen the canonical hash's surface for no traceability benefit.
15. *(phase 3, 2026-11-11)* **The §4.3 rubric's four components, as actually
   implemented** (`db/queries/q-scoring.sql`), each clamped to the
   contract's 1–9 range via SQLite's scalar `min(9, …)`:
   `score_staleness = min(9, 1 + 2×invalid + 1×never + 1×missing)`;
   `score_blast = min(9, 1 + cap_autonomous + cap_gated)`; `score_readiness`
   = 9 when an autonomous capability exists with live staleness work to
   react to, 6 when only autonomous capabilities exist, 1 when only gated
   capabilities exist and zero environments are registered (the one hard
   blocker this portfolio has today), 4 when gated capabilities exist and
   environments are registered, else 2 (nothing dispatchable); `score_precedent`
   = 1 with zero findings (honest baseline, not a zero that would out-rank a
   bad track record), else `min(9, 1 + round(avg finding score))`. Ties
   break toward cheaper-to-start per §4.3: secondary sort is
   `score_readiness DESC` (a readier item needs less setup), tertiary
   `initiative_id ASC` for full determinism.
16. *(phase 3, 2026-11-11)* **`recommendations.capability_id` stays NULL at
   phase 3.** The rubric scores at initiative grain (as §4.3 directs,
   "reuse the … instinct at initiative grain"); binding a specific
   capability per recommendation is phase 4's brief-generation job, not
   phase 3's scoring job. `required_gate` is still computed and stored now
   (from the initiative's registered capabilities' approval classes) so
   phase 4 has it without re-deriving.
17. *(phase 3, 2026-11-11)* **`implications` backfills from existing R1
   history via a new rule, R3, rather than staying empty.** BUILD-SPEC §3.1
   groups `implications` with `score_runs`/`recommendations` under
   "Implication & ranking," and the table ships in migration 0005 — leaving
   it permanently empty would fail its own §3.4 accounting entry's spirit
   ("deliberately-absent-with-reason," not "never populated by design").
   R3 (`db/queries/r3-implications-projection.sql`) projects
   `clock_invalidation_events` into `effect_kind='clock_invalidated'` rows,
   idempotently (`INSERT OR IGNORE` against the table's own UNIQUE
   constraint) — R1 remains the sole authority on which clocks flipped and
   when; R3 only generalizes the shape for phase 4+ effect kinds.
18. *(phase 3, 2026-11-11)* **A rebuild-from-scratch mistake, caught and
   reverted.** Verifying the snapshot-must-contain-every-migration rule
   (item 10) by deleting `state/portfolio.db` and rebuilding from
   `schema.sql` alone correctly proved the schema was complete — but it also
   silently discarded phases 0–2's `decision_log`/`audit_runs` history,
   which §3.2 forbids ("no facts are deleted") and §7 requires permanent
   ("a silent pass is as unpublishable as a loud fail"). Recovered via
   `git checkout -- state/portfolio.db` (the file is committed precisely so
   this recovery is possible) and migration 0005 re-applied through the
   normal incremental path (`apply_ddl` against the existing ledger), never
   a fresh rebuild, on the real store again. The scratch-rebuild diff check
   itself remains correct practice — it just belongs in `/tmp`, never
   against `state/portfolio.db` directly.
19. *(phase 4, 2026-11-11)* **`owner_gate` was a blanket `'user_gated'` for
   every project kind at seed time — phase 4's golden run exposed that this
   couldn't distinguish a software-only project from one that structurally
   needs 1TR or enrolled fleet hardware, which is exactly backwards from
   the PROPOSAL's own success metric ("recon is current, fuzzing hasn't
   started, no fleet project exists yet… recommends project 1"). Content-
   aware fix in `parse_project_lifecycle` (`classify_owner_gate`): checks
   each project's own `PROPOSAL.md` text for verbatim markers, in priority
   order — `enrolled` (case-insensitive) → `user_gated_fleet_hardware`;
   `1TR` → `user_gated_plus_1tr`; neither → `user_gated` (software-only).
   Verified against the real text: project 1 matches neither marker,
   project 2 matches `1TR` (×2) and no `enrolled`, project 3 matches
   `enrolled` (×8) and one incidental `1TR` mention (about a legitimate 1TR
   change *it detects*, not a gate on project 3 itself — `enrolled`'s
   priority over `1TR` resolves that correctly). Reparsed every run
   (`UPDATE initiatives SET owner_gate = ?`), never a one-time guess; the
   classification's basis is recorded in `meta` (`owner_gate_basis:<slug>`)
   rather than overwriting `initiatives.provenance_id`, which would have
   wrongly re-attributed the row's *other* columns (name/kind/status/
   proposal_ref) away from their real seed source.
20. *(phase 4, 2026-11-11)* **Clock anchors now resolve to the most
   recently asserted matching claim, not whichever parsed first.**
   `vuln_res/knowledge/INDEX.md` has a real case of this:
   `build-test-clippy-fmt-clean-2026-11-10` and `-2026-11-11` both match the
   `knowledge:build-test-clean` clock's anchor substring, and the old
   `ORDER BY ingested_at LIMIT 1` could anchor to whichever happened to be
   ingested first in file order rather than the newer re-confirmation.
   Changed to `ORDER BY asserted_at DESC LIMIT 1` in `seed_clocks`. This
   only affects a *fresh* seed (clocks are `ON CONFLICT(surface) DO
   NOTHING` once created) and doesn't change any already-seeded clock's
   recorded state in the live store — confirmed it doesn't matter for
   today's actual data either way, since every affected clock is already
   correctly `invalid` from events postdating even the newer anchor; the
   fix is about correctness going forward, not a behavior change today.
21. *(phase 4, 2026-11-11)* **`required_gate` used the most-permissive
   capability present; corrected to the most-restrictive.** The phase-3
   golden run's own output caught this: `vulnres_suite` has 3 autonomous
   capabilities and 4 `user_gated` ones, and the old logic reported `"none
   (autonomous capability)"` because *an* autonomous capability existed —
   dishonestly optimistic for an initiative where most of its registered
   capabilities actually require approval. `tools/supervisor.py`'s
   `_required_gate` now checks `gated_plus_1tr` → `user_gated` →
   `autonomous`-only, in that order, before falling back to the
   initiative's own `owner_gate` (for projects 1–3, which have zero
   capabilities parsed yet). Score_run #1's stored `recommendations.
   required_gate` value for `vulnres_suite` (`"none (autonomous
   capability)"`) is superseded by every score_run from this phase
   onward — history preserved per §3.2, never edited in place.
22. *(phase 4, 2026-11-11)* **`v_phase_coverage`'s hardcoded "zero
   environments"/"(empty)" wording broke the first time it stopped being
   true.** Between phase 3 and phase 4, a real environment
   (`vm-sec-research-25d125`, approved for the `vm_sec_research`/bputil-eval
   track specifically) was registered by a concurrent track's work — the
   first nonzero `environments` count this view has ever seen. Its notes
   for `vulnres_suite|execute` and the generic projects-1-3 `execute`
   branch both hardcoded the word "zero" (or "(empty)") next to an
   interpolated live count, producing a literal self-contradiction ("zero
   environments (1)") in the generated brief. Fixed the wording only — the
   *state* stays `'blocked'` for all four initiatives, confirmed still
   correct against `environments/SCHEMA.md`'s own rule ("approved_for is
   scoped, not blanket"): this environment isn't approved for
   `vulnres_suite`/project 1-3's execute-phase work, so nothing about who's
   blocked changed, only how honestly the note describes why.
23. *(phase 4, 2026-11-11)* **Known limitation, flagged rather than fixed
   under this phase's time budget: `'never'`-state clocks have no
   transition rule at all.** The same real environment registration (item
   22) exposed this: `environments:first-registered` is still `state=
   'never'` in the brief's "Staleness" section even though an environment
   now genuinely exists — because R1 (`r1-event-invalidates-clock.sql`)
   only ever flips `state='live'` rows to `'invalid'`; nothing in the
   current rule set ever moves a clock OUT of `'never'`. The seed comments
   for these three `never` clocks (`fuzz-targets:first-built`,
   `environments:first-registered`, `fleet-enrollments:first-list`) were
   written when "no environment/target/enrollment exists at all" was a
   permanent structural fact, not a transient one — that assumption just
   broke for environments specifically. Fixing it properly means a new
   rule (deciding what a `'never'` clock transitions TO: straight to
   `'live'` if the new evidence is itself a sufficient anchor, or to
   `'missing_evidence'` if it only partially satisfies the clock's original
   condition — this environment satisfies "an environment exists" but not
   "an environment approved for this surface exists", which argues for the
   latter) — deliberately deferred rather than rushed in under this
   phase's scope (brief generator + tickets + the owner_gate/required_gate
   corrections above), since an under-tested state-transition rule is
   worse than an honestly-flagged gap. Revisit before any phase that
   depends on `'never'`-clock transitions behaving correctly.

---

## 4. Analysis engine (the computations, now as queries)

### 4.1 Implication graph
Event → affected-objects propagation (file-level first, content-aware later). A commit
touching path-set P ⇒ capabilities whose coverage intersects P get dependent clocks
validated/invalidated; knowledge entries asserting "clean as of commit C" for a file in
P move into `contradictions` vs. the new evidence. `db/queries/` names these rules.

### 4.2 Phase-coverage map (APT framing operationalized)
Each Initiative carries a phase vector over `recon / build / execute / triage-learn /
persist-report`. The fused view renders one table: which phases exist, green/stale/
never-run, where overlap is, where blind seams are (recon green, execution capability
exists, zero environments ⇒ execute phase structurally blocked — a *state* fact, not
complaint).

### 4.3 Scoring + ranking (deterministic)
Reuse the proven `vulnres-triage` instinct at initiative grain — 1–9 composite of
staleness weight, blast radius, readiness (a recommendation whose approval gate is
unfulfillable today scores honestly low), rubric precedent. Top 3 into the brief; ties
break toward cheaper-to-start. Same inputs ⇒ same order, verified via `score_runs`.

### 4.4 Decision brief + dispatch tickets
Brief sections: fused picture (every claim `[source: provenance ref]`), staleness top
clocks, phase-coverage table, do-next top-3, needs-a-human list, provenance appendix, —
and (Phase 5 on) **a "simulate: what would an adversary find?" section**, §5.5. Dispatch
tickets stay text-only named blocks (`DISPATCH: <capability>`) with scope invariants
and required gate; approval is always the user's, in the conversation; every approval
and execution lands in `dispatch_tickets` + `decision_log`.

---

## 5. TTP layer: research-grounded adversary simulation (Phase 5)

### 5.1 What "simulate the TTPs" means, and doesn't

Simulated is the **adversary's decision loop, not their tooling**: profiles choose
phases, choose techniques, and the fused state is interrogated — via reviewed SQL only —
to answer, per technique: *would anything in this portfolio's current data have detected
or limited this, how fast, and through which existing capability?* No attack code, no
payload generation, no execution of anything against any host. Every gap probe is a
*question about our evidence*, and every recommendation it raises goes through the same
escalation ladder as everything else. Scenarios run inside the DB; their outputs are
text in briefs. This is table-top red-teaming with receipts.

### 5.2 The pinned TTP research baseline (build-time input)

Pin ATT&CK **v20.1 (October 2026)** — verified current at spec time from
`attack.mitre.org/resources/updates/`; record the actual STIX bundle URL + SHA at build
time in `meta`. The v20 release is the research justification and is unusually pointed
for this portfolio:

- **First AI-enabled adversary techniques** — Direct Prompt Injection (T1699), Indirect
  Prompt Injection (T1698), AI-Enabled Exfiltration (T1700), Anti-Automation Evasion
  (T1696/001-002), Impair Autonomous Defenses (T1685/007), AI Result Poisoning
  (T1608/007), Steal Application-Specific Passwords (T1697). Directly relevant: several
  target agent-driven defensive pipelines *like this portfolio's own agent fleet*, which
  makes them first-class must-model items, not trivia.
- **T1195/001 "Compromise Software Dependencies and Development Tools" promoted to
  v2.0** (major change) — the exact class of threat a repo whose staleness infra
  watches `Cargo.lock` cares about; the mapping should treat any dependency-audit
  capability as the potential detector for it.
- **New/updated groups** — NIMBUS MANTICORE (G1059), The Gentlemen (G1058), Salt
  Typhoon major update (G1045 v2.0), APT38 v4.0, Gamaredon, Scattered Spider (v3.0);
  Campaigns: 2026 U.S. Water Utilities Attacks (C0066), AI-Assisted Breach of Mexico's
  Government Infrastructure (C0064) — the first ATT&CK campaign framed as AI-assisted.
- Structural resources worth ingesting alongside techniques: **detection strategies and
  analytics counts per technique** (Enterprise: 703 strategies / 1770 analytics in v20)
  as *prior art for what detection looks like* when grading our `detect_via` fields.

`ttp/LIBRARY.md` records: the pinned subset (store *all* Enterprise techniques' IDs in
the DB, but map only the subset relevant to this portfolio's surfaces), the selection
rubric for what gets mapped (only surfaces this portfolio actually has or is scheduled
to have — no LARPing defenses that don't exist, which would fake coverage), and the
re-pin procedure.

### 5.3 Adversary profiles (`ttp/profiles/*.md`)

Start with three, each an honest model whose *program-level sequencing* is the thing
being simulated (the PROPOSAL's APT-mindset, made computational):

1. **`patient-fleet.md`** — Salt Typhoon / G1045-class: long-dwell, infrastructure
   concentration, telecom-style patience; primary interest = fleet drift invisibility
   (project 3's territory) and valid-accounts persistence. Bluest: "detection delay is
   the attacker's friend" — exactly the v20 profile.
2. **`opportunistic-supplychain.md`** — T1195/001-era: doesn't pick you, waits in the
   dependency path; the adversary this repo's own static sweeps and audit clocks exist
   to detect. Primary interest = build-time trust, fixture/provenance grooming.
3. **`agent-directed.md`** — the v20 novelty: an adversary whose techniques target the
   agentic pipeline itself (prompt injection T1698/T1699, impair autonomous defenses
   T1685/007, AI result poisoning T1608/007). Persona models: *this portfolio's own
   supervisor, orchestrators, and reporters are the attack surface*. Its gaps feed the
   supervisor's self-hardening recommendations honestly (e.g. "an indirect prompt
   injection in a parsed knowledge file could steer briefs — which capability validates
   ingestion?").

Each profile: skill level, patience, phase vector (init/recon → exploit → persist →
expand → rinse), technique preferences per phase drawn from mapped TTPs, and stop
conditions.

### 5.4 Simulation mechanics

A scenario run seeds each profile with a phase sequence; for each step the engine:

1. Pulls technique candidates for the phase — via reviewed SQL joining
   `v_technique_phase` (or `phase_tactics` directly), `technique_groups` for the
   profile's class-attested usage set, and `technique_platforms` for macOS/surface
   relevance — then picks from them per the profile's stated preferences. Candidates
   the profile *should* find tempting per attested group usage but which the fused
   state renders dead-ends are recorded as `sim_steps.basis = 'deterred: <reason>'`
   with provenance — deterred steps are as informative as blind ones.
2. Answers the three coverage questions from `ttp_mappings` + staleness + capability
   rows: *detect? (which capability, in what state) / limit? / how fast?* — each with
   row-level provenance.
3. Emits per-step `sim_gaps`: where verdict `uncovered`/`asserted_unproven` or clock
   `never|invalid`, phrase it as a *gap probe*, e.g. "T1021/004 SSH over enrolled fleet
   Macs: detection = fleet drift watch (not built); clock = never. Gap: a patient
   adversary on an unmonitored enrolled Mac has a detection latency of ∞ under current
   state."
4. The profile then *decides its next phase like an adversary would* — investing where
   probes came back blind — and that decision trail is itself output: the brief's
   "what the model would focus on next" is a pressure map for our own scheduling, which
   is exactly the PROPOSAL's "decide which phase to invest in next" instinct, inverted.

### 5.5 Brief integration + guardrails

- New brief section **"Simulate"**: per-profile verdict counts, the top 3 gap probes by
  detection-latency math, and any recommendation the probes raised — each carrying
  `required gate:` as always.
- New brief line — **"TTP self-check"**: every technique cited as `covered` must have a
  `ttp_mappings.evidence_id` (the schema enforces this at load time — `covered` with
  NULL evidence is structurally prohibited); additionally any `covered` claim on a
  `technique_detcount = 0` technique is rendered with a scrutiny flag. What the schema
  can't pre-verify, the self-check does: verdict/source coherence per mapping row.
- Hard boundaries, restated for this layer specifically: simulations never generate
  payloads, never produce runnable artifacts, never leave the DB/briefs, never map a
  technique to an *execution* recommendation — mapped gaps route to defensive
  capabilities only (recon, fuzz harness, drift watch, triage), and anything drifting
  toward Apple-platform territory trips the STOP-AND-ASK marking like everything else.
- Profile/technique additions are reviewable text (`ttp/`), diffs in plain git. ATT&CK
  re-pins render a release-diff into the brief via `v_repin_diff` (§3.3's A6) and land
  as needs-a-human items — never as a silent content refresh.

---

## 6. Wiring map (how everything connects)

```
 sources (1–8) ──parsers──▶ portfolio.db (provenance-carrying rows)
   git events ─────────────▶ events → clock_invalidation_events → implications
   staleness_clocks ───────▶ score_runs → recommendations (db/queries/*.sql)
   capabilities + approval classes ─▶ dispatch_tickets (approved by user only)
   ttps (pinned STIX) + mappings + profiles ─▶ sim_scenarios → sim_gaps ┐
                                                                          ├─▶ briefs/*.md
 fused-portfolio.md / decision-log.md ◀── regenerate-on-every-run ────────┘
```

Every arrow is either a parser (sources → DB), a query (DB → analysis rows), a
generator (analysis rows → brief text), or a user-gated dispatch. No other edges exist.

---

## 7. Escalation ladder + self-audit (verbatim contract, enforced at runtime)

Copy the PROPOSAL's two lists into `README.md` word for word, then implement:

- Every run starts with `tests/self-audit.md`: forbidden-pattern grep over run artifacts
  (writes outside `state/`/`briefs/`/`ttp/`/`db/migrations` additions; any proposed env
  creation/reuse phrased as anything but "requires user"; mutation vocabulary in
  recommendations; gated-capability ticket missing `required gate:`; **any `.sql` used
  by a brief that doesn't live in `db/queries/`; any sim artifact containing executable
  code or a payload-shaped blob**). Audit failure ⇒ brief suppressed, failure recorded in
  `decision_log`, user informed. **No brief ships with a failed audit.**
- Apple-platform drift ⇒ surfaced verbatim with STOP-AND-ASK; never silently re-scoped.
- Standing schedules ⇒ "recommendation; your approval required," never created.

---

## 8. Phased build (execute in order; acceptance = evidence recorded in `decision_log`)

### Phase 0 — Contract, scaffold, database empty-shell
Build: directory scaffold; `db/schema.sql` (meta/provenance/runs/decision_log tables
only) applied to `state/portfolio.db`; `db/migrations/0000-add-meta.sql`;
`ontology/sources.yaml` (registry entries, parsers deferred); `README.md` escalation
ladder + runbook; `tests/self-audit.md` v1.
**Accept:** DB opens, migrations apply idempotently (run twice), provenance-null query
returns 0 across existing tables; self-audit passes on empty scaffold; decision_log has
"Phase 0 verified." Commit.

### Phase 1 — Two-source fusion into the DB
Build: `ontology/SCHEMA.md` (full object/link definitions + source→table mapping);
parsers for sources 1–2; `initiatives`/`evidence`/`links` load path; first
`fused-portfolio.md` generated; parse-failure path exercised.
**Accept:** ≥5 objects spot-check to real source lines; M8–M10 evidence chain resolves
to ONE initiative without fragmentation, and the `milestones` table holds all M0–M10
rows with `milestone_log` entries dated from the real log (including its 'Next up'
lines — a decision-engine input); a deliberately mangled source produces a
`parse_failures` row, not a silent skip. Commit.

### Phase 2 — Full fusion + staleness clocks + file-level implication (as SQL)
Build: sources 3–7; `staleness_clocks`, `events`, `clock_invalidation_events`,
`contradictions`; regenerate view. Live backlink test case already in-repo:
`verify-baseline-no-size-cap` (sweep 2026-11-11-001) vs. clean-as-of knowledge entries
must surface a contradiction row.
**Accept:** clock table has ≥1 `never` and ≥1 live clock with correct invalidators; a
described synthetic git event flips a dependent clock on regeneration; knowledge-entry
kinds parse into typed `evidence` rows (environment/target-status/general per INDEX.md's
own footer); the accounting query (`db/queries/accounting.sql`, §3.4) runs and its
output — including honestly-empty tables like `environments`, `fuzz_targets`,
`fleet_enrollments`, `schedules` — is committed as a decision-log attachment, with every
zero-row table ticked against the §3.4 map. Commit.

### Phase 3 — Phase-coverage map + deterministic scoring
Build: §4.2 map and §4.3 rubric as reviewed SQL in `db/queries/`; `score_runs` anchors.
**Accept:** byte-identical ranking across two runs from identical state; each
recommendation carries four provenance-backed components. Commit.

### Phase 4 — Briefs, tickets, sharpened implication; THE golden run
Build: brief generator from DB + reviewed queries; ticket format; content-aware
implication joins (fixture/knowledge);
**Accept — the PROPOSAL's success metric run for real:** a full run on today's repo
produces a brief recommending *project 1* with the correct required gate, a complete
needs-a-human list, zero execution; `git status` shows nothing outside
`projects/supervisor-agent/` changed. Commit.

### Phase 5 — TTP layer: pin, map, profile, simulate
Build: STIX bundle download + hash pin into `meta`; `ttps` ingest; `ttp_mappings` for
the selection-rubric subset, seeded against the v20 highlights (§5.2) plus the
transitive set this portfolio's surfaces imply; the three profiles (§5.3); simulation
engine (§5.4) using reviewed queries only; "Simulate" + "TTP self-check" brief sections.
**Accept:** (a) pinned hash in `meta` matches the fetched bundle; (b) every
`covered` verdict produced during a full sim run cites a real evidence row — one
deliberately fabricated coverage claim is injected and the self-check marks it
`asserted, unproven` (proof the gate trips, then removed); (c) three profile runs each
emit ≥1 honest gap probe (today's true state guarantees several — e.g. agent-directed's
"what validates ingestion?" and patient-fleet's ∞ latency on unmonitored enrolled Macs);
(d) no sim artifact contains executable content (self-audit v2). Commit.

### Phase 6 — Evals, audit hardening, agent packaging
Build: `tests/SCENARIOS.md` — (a) Phase 4 golden run, (b) "schedule-me" ⇒ recommendation
never creation, (c) Apple-territory request ⇒ STOP-AND-ASK surfaced, (d) unparseable
sources ⇒ degraded-mode brief with zero fabricated facts, (e) empty DB ⇒ honest
about-nothing-verified brief, (f) sim-run determinism (same seed+state ⇒ identical
scenario tables). Wire self-audit as pre-brief gate. Build
`.claude/agents/vulnres-supervisor.md` in the exact shape of
`.claude/agents/vulnres-orchestrator.md`, plus the direct-read fallback per
`sweep-reports/2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md`
and `vuln_res/plans/06-orchestration-and-scheduling.md` — the fallback stays the
supported path; nothing gates on the harness registry being fixed.
**Accept:** all six scenarios pass with recorded evidence; a deliberately non-compliant
brief is demonstrably suppressed; decision log closes the build; a dated entry with
commit hash appended to `progress/milestones.md` per that file's own rules.

---

## 9. Invariants checklist (restate in `tests/self-audit.md`, verify every phase)

1. Writes only ever to `projects/supervisor-agent/{state,briefs,db,ttp,tests}`.
   Grep-provable per run.
2. Every DB row and every brief claim has provenance; the provenance-null query is
   always 0, and every fact names a source line.
3. No execution of, or configuration for, any capability's tooling — by the supervisor;
   tickets are text the user approves.
4. `environments/` tables are read-only mirrors forever.
5. Parse failures are first-class rows, never papered over.
6. Determinism: identical state ⇒ identical ranking and identical seeded sims;
   breaks are regressions.
7. No adversarial content in sim artifacts — decision models and gap probes only.
8. The escalation ladder lives in `README.md` word-for-word from PROPOSAL.md; changing
   a single word is a new proposal per the PROPOSAL's open-risk clause, not an edit.
9. Database is source of truth; markdown mirrors are regenerated views; any divergence
   is a logged violation, not a judgment call.
