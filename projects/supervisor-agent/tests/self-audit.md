# Self-audit checklist — v1 (BUILD-SPEC §7)

Run at every session start and every run, and before any brief ships. Checks
implemented in `tools/supervisor.py audit` are marked **[auto]** — that command is
the gate; the CI-equivalent manual checks are marked **[man]** for the coordinator
session. `audit_runs` records EVERY result, pass and fail; audit failure means the
brief is suppressed and the failure is recorded in `decision_log`.

## A1 — Database opens, integrity holds **[auto]**

```
PRAGMA integrity_check  →  'ok'
```

## A2 — Migration ledger intact **[auto]**

Every `db/migrations/[0-9]*-*.sql` on disk appears in `meta.applied_migrations`.
A migration on disk but absent from the ledger means the DB ran someone's
unrecorded state — FAIL.

## A3 — Provenance never null **[auto]**

```
SELECT count(*) FROM <table> WHERE provenance_id IS NULL  →  0
```

across every table that carries a provenance_id column (BUILD-SPEC §3.5 scope
rule: `meta`, `runs`, `decision_log`, `audit_runs` are exempt by construction —
each row's provenance IS the run that wrote it).

## A4 — No forbidden patterns in run artifacts **[auto]**

Grep the generated views (`state/*.md` mirrors) and everything in `briefs/` for:

- `tart create`, `tart run`
- `cargo fuzz`
- `ssh ` (as a proposed action, not a routing word — reviewer judgment on hits)
- `wrapper.rs`

A hit is either a mutation vocabulary leak into a recommendation or proposed
execution — both FAIL until resolved. (README/BUILD-SPEC/tests deliberately quote
these words as doctrine; they are not run artifacts.)

## A5 — Write scope grep-provable **[auto]**

Every write-class call in `tools/*.py` resolves under
`projects/supervisor-agent/{state,briefs,db,ttp,tests}`. This file's own were
reviewed at v1; any new tool call pattern beyond those gets a manual look.

## A6 — Repo scope **[man, coordinator session]**

Before the post-run commit: `git status` shows changes only inside
`projects/supervisor-agent/` (plus `progress/milestones.md` ONLY for the dated
build-closure entry §8 phase-6 names, and never silently). Anything else
changed ⇒ the run wrote outside its envelope ⇒ FAIL.

## A7 — Gated-capability tickets carry their gate **[auto, phases 4+]**

Every dispatch ticket whose capability's approval_class is not `autonomous`
contains the literal string `required gate:`. Grep `briefs/*.md` for
`DISPATCH: <capability>` blocks missing it ⇒ FAIL.

## A8 — Briefs use reviewed SQL only **[auto, phases 4+]**

Every analytical claim in a brief references a named query under `db/queries/`;
no brief fabricates inline SQL. Grep for swung query text not resolvable to a
file there ⇒ FAIL.

## A9 — Parse failures are first-class **[man/auto, phases 1+]**

A source that failed to parse appears in `parse_failures` with provenance and
its authority is 0 for that run. "It looked parseable enough" ⇒ FAIL.

## A10 — Sim artifacts are inert **[auto, phase 5+]**

Anything the simulation layer produces (scenario tables, gap probes, brief
sections) contains decision models and questions only — no executable code, no
payload-shaped blobs. Grep sim brief sections for `#!/`, `curl `, `python3 -c`,
`osascript` ⇒ FAIL.

## The two standing STOP rules (per PROPOSAL.md, enforced every phase)

- Apple-platform drift ⇒ surfaced verbatim with STOP-AND-ASK; never silently
  re-scoped.
- Standing schedules ⇒ "recommendation; your approval required," never created.
