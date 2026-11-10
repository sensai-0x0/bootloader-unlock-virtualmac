# Neuropunk paper — the aesthetic

A name for what `tokens.css`, `shared.css`, and `components.md` are already
doing, written out so the next component built for this dashboard has
something to be judged against instead of improvised from scratch.

## The premise

Two materials that don't belong together, forced into one object:

- **Paper.** A ledger, a carbon-copy bulletin, a stamped-and-filed report.
  Paper is slow, authoritative, and permanent — once a line is entered it is
  part of the record. This is where the "20-year veteran of paper
  dashboards" persona and the flat ledger-row layout already come from.
- **Signal.** An oscilloscope trace, a phosphor readout, the wobble and
  dropout of a neurofunk bassline — electronic, processed, and honest about
  its own degradation. Signal doesn't pretend to certainty it doesn't have;
  it shows noise when there is noise.

A security-research dashboard is, underneath, exactly this collision: a
human wants a permanent, citable *record* (paper) built out of
machine-read, sometimes-degraded *measurements* (signal). The aesthetic's
whole job is to hold both without one swallowing the other. If it only did
paper, you'd get a plain data table. If it only did signal, you'd get a
glowing terminal screen with no sense that anything on it is a durable
finding. Neither alone is the brief.

## Why "punk"

Not decoration — a refusal. This dashboard explicitly rejects the SaaS
dashboard's whole social contract: rounded cards reassuring you everything
is fine, a CTA telling you what to do next, a gradient hero selling the
product back to you. A paper ledger doesn't sell you anything; it just
tells you what was measured, flatly, and expects you to act on your own
judgment. The "no buttons" rule is the punk part, not the paper part — a
refusal to let the interface make the call for you, which matters doubly on
a tool whose own contract (`ReadOnlyUnlessGated`, `FEATURE-PLAN.md`) forbids
exactly that.

## Material vocabulary

Specific, recurring motifs — not a mood board, a kit of parts every new
component should be built from:

- **The hairline rule.** The only line in the system. No shadows, no
  borders-as-decoration, ever. A rule means "this is where one record ends
  and the next begins," nothing else.
- **The stamp.** A disclosed or fixed finding doesn't just change color —
  it gets stamped, the way a librarian or a customs officer stamps a
  physical record. A small, slightly-off-grid ink mark, not a smooth
  badge. This is the one place a tiny bit of imperfection (a 1–2° rotation,
  a slightly irregular edge) is deliberate: a stamp is a human or mechanical
  act, not a rendered state.
- **The carbon copy.** A diff isn't a before/after table — it's a corrected
  ledger line: the old value struck through in `--paper-white-dim`, the new
  value written fresh beneath it in `--paper-white`, the way a handwritten
  ledger gets corrected without erasing the original entry.
- **The phosphor trace.** A thin, continuous line — never a bar, never a
  filled area — is how this system shows anything over time (sweep
  cadence, confidence history). It should look like it's being drawn by a
  pen that's still moving, not like a finished chart.
- **Signal noise as honesty.** The one genuinely load-bearing idea in this
  document: **confidence is rendered as texture, not just as a word.** A
  `Measured` reading draws crisp and still. An `UntrustedRead` or
  `Unmeasured` reading draws with a visible, subtle dither/static over the
  affected value — not a warning icon bolted on, the value itself looking
  less certain. This makes `MeasuredTruth` (never claim more than was
  measured) something you can *see* before you've read a single label,
  which is a stronger honesty guarantee than text alone gives you.

## Color and type, restated with the reasoning sharpened

`tokens.css`'s palette already does the paper/signal split; naming why:
`paper-white` and its dim variant are the *paper* half (static, legible,
the record), `signal-green` and its muted variant are the *signal* half
(live, measured, provisional), and `amber-flag` is the single rupture
between them — the one color that means "a human has to look at this,"
spent nowhere else. Big Shoulders is the paper half's typeface (stenciled,
structural, the way a form's field labels are printed); Fragment Mono is
the signal half's (every number on this dashboard came out of a machine
reading something, and it should look like it).

## Interaction grammar — "high interaction" without buttons

High interaction here means **more of the interface responds to attention
and motion**, not that there are more controls to click. Five patterns,
each a direct-manipulation idea rather than a command:

1. **Hover previews, click pins.** Hovering a ledger row updates a
   persistent side rail with that row's detail, live, with no navigation.
   Clicking the row (the existing `<details>` mechanism) *pins* that detail
   open so it survives the next hover — the same "glance vs. commit"
   distinction a paper ledger gives you for free when you run a finger down
   a column before actually stopping to read an entry.
2. **The loupe.** Hovering any `--font-data` numeral (a score, a hash
   fragment, a timestamp) briefly grows a small magnified overlay of just
   that value, the way you'd hold a magnifying glass over a printed ledger
   rather than reach for a tool. Exact values stay available without
   pre-committing screen space to showing every digit of every row at once
   — keeps density low, per the brief's "low information density" rule,
   while still making precision available on demand.
3. **The scrub timeline.** Sweep history (today a static vertical rail list
   in `view-1-sweep-findings.html`) becomes a horizontal line you drag a
   position along, each past sweep a tick mark on it. Dragging re-renders
   the ledger above as of that sweep. A scrubber is a direct-manipulation
   control, not a button — there's no "previous sweep" action to click,
   just a position to be at.
4. **Keyboard tracing.** Arrow keys move focus row to row in a ledger,
   `Enter`/`Space` opens the focused row (native `<details>` behavior,
   already free) — reading the dashboard by tracing down it with a finger,
   translated to keys, instead of scanning a page of open text.
5. **Degrade on distrust.** The signal-noise-as-honesty idea above is also
   an interaction rule: as data gets less certain, the UI gets *less
   responsive to being stared at* — a `Measured` value's loupe zooms in
   crisply; an `Unmeasured` value's loupe shows the same static you'd see
   at a glance, because zooming in on a number that was never actually read
   shouldn't manufacture false precision.

## A catalog of components this implies

Beyond the three already speced in `components.md` (posture-confidence
tick, security-mode tick, invariants checklist), built from the vocabulary
above:

| Component | What it replaces | Material |
|---|---|---|
| Stamp mark | a colored "resolved" badge | the stamp |
| Carbon-copy diff row | a before/after table | the carbon copy |
| Phosphor trace | a sparkline/bar chart | the phosphor trace |
| Noise-textured value | a confidence label next to a number | signal noise as honesty |
| Loupe tooltip | a persistent full-precision column | the loupe |
| Scrub timeline | a "previous/next sweep" pager | — |

None of these exist in the two shipped views yet. This document defines
them; building them into `view-1-sweep-findings.html` and
`view-2-campaign-overview.html`, or into the posture/evidence views
`FEATURE-PLAN.md` scoped, is the natural next step — not done here, since
the ask was to define the aesthetic, not yet to rebuild the views around
it.

## What this rejects

Said once, plainly, so it's checkable against anything built next:

- Any badge, pill, or card with a border-radius.
- Any chart that's a filled bar or area rather than a drawn line.
- Any confidence or severity value stated only in text, with no visual
  correlate.
- Any interaction that exists to be clicked once and forgotten, rather than
  responded to continuously (hover, drag, focus).
- Any affordance, anywhere, that could be mistaken for "apply" or "revert."
