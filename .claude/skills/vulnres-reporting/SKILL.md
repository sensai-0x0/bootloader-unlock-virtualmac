---
name: vulnres-reporting
description: Generates a daily, weekly, or monthly report of this project's vuln_res/ sweep activity and progress/milestones.md entries for the specified period, and writes it to reports/{daily,weekly,monthly}/. Invoke with a period argument ("daily", "weekly", or "monthly") and an optional anchor date (defaults to today). Use when asked for "a daily report", "this week's report", "summarize last month's findings", or similar.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
---

## Project scoping — read this before anything else

This skill is **project-scoped**: it lives at `.claude/skills/vulnres-reporting/` inside
`the-ant-experiment`, not in `~/.claude/skills/` — it only means anything against this
repo's own `vuln_res/` and `progress/` history. If this session's available-skills
listing doesn't show `vulnres-reporting` (the same project-level-discovery gap already
confirmed for `.claude/agents/vulnres-*`, see
`vuln_res/sweep-reports/2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md`),
read this file directly and follow it rather than retrying the native invocation.

## Arguments

- **Period** (required): `daily`, `weekly`, or `monthly`.
- **Anchor date** (optional): defaults to today. The window ends on the anchor date and
  runs backward — 1 day for `daily`, 7 days for `weekly`, the anchor's full calendar
  month for `monthly`.

## What you do

1. **Compute the window.** `daily` → the anchor date alone. `weekly` → anchor minus 6
   days through anchor (7 days inclusive). `monthly` → the 1st through the last day of
   the anchor's calendar month.
2. **Gather vuln_res/ activity dated in that window:**
   - `vuln_res/sweep-reports/INDEX.md` — every `##` sweep entry whose sweep-id date
     prefix (`YYYY-MM-DD`) falls in the window.
   - Each matching sweep's `summary.md` — findings opened, knowledge entries written,
     blockers noted.
   - `vuln_res/sweep-reports/findings-index.md` — cross-check status (`open`, `fixed`,
     `root-caused`, etc.) as of report-generation time, not just what the sweep said at
     the time — a finding opened two sweeps ago but only fixed this window counts as
     "fixed this window," not "opened this window."
   - `vuln_res/sweep-reports/exploits-index.md` — any row added or changed in this
     window. **Always its own called-out subsection, never folded into the general
     findings count** — this is the one piece of this report a reader should never be
     able to miss.
   - `vuln_res/knowledge/INDEX.md` — entries with `updated:` dates in the window.
3. **Gather project milestone activity dated in the window:** `progress/milestones.md`'s
   `## Log` section's dated `###` entries.
4. **Check the previous report in the same period's `INDEX.md`** (if any) for a brief
   "since last report" delta — open-findings count trending up or down, new vs. resolved.
   Skip this section if there's no prior report to compare to.
5. **Write the report** to `reports/<period>/<window-label>.md` using
   `reports/TEMPLATE-period-report.md`'s structure, where `<window-label>` is:
   - `daily`: `YYYY-MM-DD`
   - `weekly`: `YYYY-MM-DD-to-YYYY-MM-DD` (start-to-end)
   - `monthly`: `YYYY-MM`
6. **Append one line to `reports/<period>/INDEX.md`** — never rewrite prior entries.
7. **If nothing happened in the window** (no sweeps, no milestone entries), still write
   the report — short, honest, "quiet period" — don't skip it. A gap in the ledger is
   worse than a one-line report. This mirrors the project's own `ScheduleWakeup`
   `noop`-tracking philosophy elsewhere: silence is a reportable state, not an absence of
   one.

## What you never do

- Don't editorialize beyond what the source files actually say — this is a rollup of
  existing records, not a new analysis. (Pattern-finding across findings is
  `vulnres-pattern-analysis`'s job, not this skill's.)
- Don't backfill or regenerate a past period's report once written — if asked to
  "redo yesterday's report," write a new dated note explaining the correction rather
  than silently overwriting the ledger entry, same spirit as every other append-only
  index in this project.
- Don't invent activity that didn't happen to make a quiet period look busier.

## Output contract

- `reports/<period>/<window-label>.md` (new file, from the template).
- One appended line in `reports/<period>/INDEX.md`.
- No other file touched — this skill only reads `vuln_res/` and `progress/milestones.md`
  and writes to `reports/<period>/`.
