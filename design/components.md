# Components

Specs for the custom components used by both views. No `<button>` anywhere —
every interactive element below is a native disclosure, radio, or anchor
element styled to not look like one, so keyboard and screen-reader behavior
comes for free instead of being reimplemented.

## Ledger row (`.ledger`)

A `<table>`-free row system built from `<details>`/`<summary>` pairs, one per
finding or exploit. `<summary>` carries the collapsed row's grid of columns;
clicking anywhere on the row (not a button, the whole row) toggles the
`<details>` open, revealing the record's body below it, indented one level
into `--graphite-700`.

- Collapsed row: CSS grid, columns per view (see view specs).
- Rule: `border-bottom: 1px solid var(--hairline)` — the only line style.
- Hover / open state: `background: var(--graphite-700)`, text promotes from
  `--paper-white-dim` to `--paper-white`. No shadow, no scale, no border
  color change.
- Expanded body: definition-list style key/value pairs in `--font-data`,
  left-indented to align under the row's second column.

## Severity glyph (`.severity`)

Three small cells in a row, each either lit (`--signal-green`) or dim
(`--hairline-strong`), reading left to right as **reachability →
memory-safety-weight → blast-radius**, each 1–3. This replaces a colored
severity badge with a component that teaches vuln_res/'s actual scoring
formula instead of hiding it behind one color.

```
●●○   =  reachability 2, weight-irrelevant (always lit, weight is binary-ish 1-3 too), blast-radius 1
```

Each cell is a `<span>` with `data-lit` or not; a `title` attribute carries
the literal score string (e.g. `"9 (3×1×3)"`) for anyone who wants the exact
number without it being the first thing shown.

## Status rule (`.status`)

Status (`open | fixed | disclosed-upstream | false-positive |
escalated-to-human`) renders as a short tick mark plus the word itself in
`--font-structural`, never a pill/badge:

- `open` — `--signal-green`, tick is a filled square.
- `fixed` / `disclosed-upstream` — `--signal-green-muted` text with a
  `--signal-green-dim` outline tick. (`--signal-green-dim` itself is reserved
  for decorative/border use — at ~3.5:1 it reads fine as a thin outline but
  fails WCAG AA as body text, so text uses the lighter muted variant, ~6:1.)
- `false-positive` — `--paper-white-dim`, tick is a dash.
- `escalated-to-human` — `--amber-flag`, tick is a filled triangle. The only
  place amber appears.

## Status filter legend (`.legend`)

A row of the five status words, each itself the toggle — click a word to
filter the ledger to just that status; click again to clear. No separate
"filter" control or button. Implemented as checkboxes visually hidden under
each legend label (`<input type="checkbox" class="legend-toggle">` +
`<label>`), so the toggle state is native form state, not hand-rolled JS
state — the one script on the page just maps that state to a `[hidden]`
attribute on non-matching rows.

## View dial (`.dial`)

The switch between the two views. Two `<a>` elements side by side, styled as
a horizontal dial with a single moving tick mark (a 2px `--signal-green`
underline) rather than two button-shaped tabs. `aria-current="page"` marks
the active one; the tick's position is set per-page in each file's own
inline style (no shared JS needed since they're two static pages).

## Sweep manifest header (`.manifest`)

Not a card — a single ruled block at the top of view 1: sweep id and label
in `--font-data`, duration right-aligned, agents_run listed as a plain
comma-joined line underneath in `--paper-white-dim`, no separators styled as
decoration.

## Headline figure (`.headline`)

One big number (`--text-headline`, `--font-data`, `--paper-white`) with a
single small label beneath it in `--font-structural`, sentence case. Used
once per view, at the top, as the "paper bulletin leads with one tally"
hero — not repeated as a stat-tile row elsewhere on the page.
