# vuln_res/knowledge/ — compound knowledge across sweeps

Durable facts learned while running this suite, kept separate from `../sweep-reports/` because
not everything worth remembering is a vulnerability — most of what makes a second sweep
faster than the first is knowing what's *already been checked and cleared*.

## Entry format

Each file is one fact, named `<kebab-case-slug>.md`:

```markdown
---
name: kebab-case-slug
type: target-status | dependency-check | parsing-pattern | tool-note | environment
description: one-line, specific enough to judge relevance without opening the file
updated: YYYY-MM-DD
---

The fact itself. Link related entries with [[other-slug]].
```

`type: environment` entries are a special case with their own fixed schema — see
`environments/SCHEMA.md` — because they describe infrastructure state, not a research
finding, and an orchestrating agent needs to parse them reliably, not just read them.

## What goes here vs. `../sweep-reports/`

- **Here:** "fuzz target `img4_decode` has run for 6 corpus-hours against commit `<sha>`
  with zero crashes" / "`cargo audit` checked `Cargo.lock` against the advisory DB
  snapshot of 2026-11-10, clean" / "the `env.rs`/`collect.rs` `contains()` pattern from
  `../AUDIT.md` §2 was reviewed suite-wide on 2026-11-10, no third instance found" /
  "environment `tart-fuzz-01` is a disposable, network-isolated Linux container approved
  for fuzzing only."
- **There:** an actual distinct, minimized, scored bug.

## Index

`INDEX.md` is the always-read entry point — one line per fact, same discipline as a
memory index: short, current, and the first thing any agent in this suite reads before
starting work, so it doesn't re-derive something already known.
