# vuln_res/sweep-reports/ — prototype storage layer

This is the actual storage solution for the vulnerability-research suite's sweep
output, for now: **plain markdown and text files on disk, inside this repo.** No
database, no proprietary format, no store that only Claude can read — anything that can
open a text file (a shell, an editor, `grep`, another script, a human) can read a
finding directly, because it's a real file at a real path. A real database is deferred
until this is past prototype stage — this layout is deliberately simple so migrating it
later (one row per finding, one row per sweep) is a straightforward import, not a
redesign.

## Layout

```
sweep-reports/
  README.md              — this file
  INDEX.md                — sweep ledger: one entry per sweep, ever run
  findings-index.md       — cross-sweep findings index: one line per distinct finding,
                            wherever it lives, so you never have to open every sweep
                            directory to find a specific bug
  TEMPLATE-sweep.md       — template for a new sweep's summary.md
  TEMPLATE-finding.md     — template for a new finding file
  <sweep-id>/             — one directory per sweep, e.g. 2026-11-10-001-recon-verification
    summary.md            — what this sweep did, per TEMPLATE-sweep.md
    <finding-slug>.md      — one file per finding this sweep produced (if any)
    <finding-slug>.poc     — minimized PoC artifact alongside its finding, if applicable
```

`<sweep-id>` is `<date>-<sequence>-<short-label>` — sortable by filesystem listing alone
(`ls sweep-reports/` already gives you chronological order), unique even if two sweeps
run the same day, and self-describing without opening anything.

## Why "as many files as makes sense" rather than one big log

- A finding is reviewable, linkable, and diffable on its own — one file, one bug.
- A sweep's own summary stays separate from the findings it produced, so "what did this
  run do" and "what specific bug is this" are two different questions with two different
  answers, not one scrolling document.
- Grepping across `sweep-reports/**/*.md` for a keyword works immediately, with zero
  tooling, which is exactly what "available to the wider operating system" means here —
  nothing about this storage requires Claude, or any specific program, to read it.

## What every finding file must include

Per `TEMPLATE-finding.md`: a **short, plain-language description** (a non-specialist
reviewer can follow it) in addition to the full technical writeup. This is mandatory for
every finding, and especially for anything `vulnres-exploit-dev` produces — a single-bug
or multi-step-chain exploit write-up without a plain-language summary at the top is
incomplete, not just terse.
