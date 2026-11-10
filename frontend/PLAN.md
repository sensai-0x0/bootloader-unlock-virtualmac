# Build plan — vulnres-dashboard

Tracks phases, what shipped, and what the next phase should be revised
because of what the last one taught. Updated at the end of every work
block, not drafted once up front and left stale.

## Phase 0 — scaffold (done)

**Shipped:** Bun-native app (no Vite — matches `metacogna-rag`'s established
convention), `src/router.tsx` (custom, ~30 lines, no React Router), the two
views at parity with the static mockups in `../design/` (`SweepFindingsView`,
`CampaignOverviewView`), the full component set ported from
`../design/components.md` (`Ledger`/`LedgerRow`, `SeverityGlyph`,
`StatusTick`, `Legend`, `ManifestHeader`, `Headline`, `StageRule`, `Rail`,
`Dial`), `bun test` + happy-dom + Testing Library wired up, `frontend/CLAUDE.md`.

**Verified:** `bun run typecheck` clean, `bun test` — 14 pass, `bun run
build` — bundles to `dist/` (0.34 MB JS, 6.5 KB CSS), dev server smoke-tested
with `curl` (both `/` and `/campaign` return 200 with the right title — the
SPA-fallback routing works).

**Judgment — one real bug found and fixed, not just ported:** the static
`design/` mockup's severity glyph lit cells inconsistently for equal score
factors (e.g. blast-radius 2 rendered lit in one example, dim in another).
Porting it to code with a single pure function (`src/lib/score.ts`'s
`glyphCells`) forced a real rule to exist — `lit = factor >= 2` — and a test
that would have caught the old inconsistency. This is the main payoff of
"build it for real" over "it's just a mockup": ambiguity that was invisible
in static HTML became a type error / failing test the moment it had to be a
function.

**Process note, not a design one:** this repo has multiple concurrent
Claude Code sessions actively committing to `main` right now, and at one
point left an unresolved merge conflict (`fix/tier0-trust-hardening` into
`main`, conflicting in `src/state/diff.rs`) sitting in the shared working
tree. This frontend build was moved into its own git worktree
(`.claude/worktrees/frontend-dashboard`, branch `feat/frontend-dashboard`)
off the last known-clean commit specifically to avoid touching that
conflict or racing with the other session's Rust-side work. Merge this
branch into `main` only once that's resolved and someone's checked there's
no overlap (there shouldn't be — this branch only touches `frontend/`).

**Revising the plan for what's next**, based on what Phase 0 actually
needed: the original plan bundled "beautiful custom components" (stamp,
loupe, phosphor trace, scrub timeline, noise-as-texture) into one big Phase
2. Splitting that further than originally planned — each of those is a
genuinely separate interaction idea with its own edge cases (hover timing,
drag math, animation performance), and bundling them risks a phase that's
too large to judge honestly before committing. Revised:

## Phase 1 — stamp mark + phosphor trace (done)

**Shipped:** `StampMark` (hand-perturbed-quadrilateral SVG border, rotated
-4deg, `currentColor` so it always matches the status text it sits beside —
wired into `StatusTick` for `fixed`/`disclosed-upstream` only, no new call
sites needed in either view) and `PhosphorTrace` (a drawn `<polyline>`, no
fill, with the normalization math pulled out to a pure `src/lib/trace.ts`
so the zero-range/single-value edge cases are actually tested rather than
discovered as a rendering glitch). Wired into `SweepFindingsView`'s
headline, showing findings-per-sweep across the two history entries plus
the current sweep.

**Verified:** `bun run typecheck` clean, `bun test` — 23/23 pass (9 new:
`trace.test.ts`'s edge cases, `StampMark.test.tsx`, `StatusTick.test.tsx`'s
stamp-presence assertions), `bun run build` bundles clean (41 modules, CSS
grew 6.45 KB → 6.90 KB — the two new components cost under half a KB of
style).

**Judgment:** keeping `StampMark` colorless (`currentColor`) instead of
taking its own color prop was the right call — it means `StatusTick`
stayed a single source of truth for status→color, and the stamp can never
drift out of sync with the tick/label it sits next to. The one thing I'd
flag for a future pass: the stamp's hand-perturbed border coordinates are
hand-authored once, not derived — fine for two label strings today, but if
a third stamped status is added later, eyeball the border at that label's
width rather than assuming the same four points still look irregular
rather than just skewed.

**Revising the plan again:** Phase 2 as originally scoped (loupe + noise
texture) still depends on data this app doesn't have yet — `Finding` has
no `confidence` field, so there's nothing honest to drive a noise-as-texture
treatment with. Splitting that out rather than inventing a fake confidence
value just to have something to animate.

## Phase 2 — loupe tooltip (done)

**Shipped:** `Loupe` — a generic `display`/`full` wrapper, 250ms hover
delay (and real keyboard-focus support, not just `:hover` — ties into the
"keyboard tracing" interaction principle from `../design/AESTHETIC.md`
rather than being mouse-only). Wired into `SeverityGlyph`, replacing its
native `title` attribute outright: the severity glyph was already exactly
the pattern the loupe concept describes — a compact visual standing in for
an exact value — so this wasn't a new place to add interaction, it was
removing a worse (inconsistent-timing, not keyboard-reachable,
browser-styled) version of the same idea and putting the real one in its
place.

**Verified:** `bun run typecheck` clean, `bun test` — 27/27 pass (4 new:
`Loupe.test.tsx` covers the delay, mid-delay mouse-leave cancel, and
keyboard focus; `SeverityGlyph.test.tsx` rewritten to assert the glyph
carries no inline text and that focusing it reveals the formatted score),
`bun run build` bundles clean (7.37 KB CSS, up from 6.90 KB).

**Judgment:** glad this replaced `title` rather than sitting alongside it —
running both would have meant two overlapping tooltips on a slow hover
(the browser's native one and the loupe's), which is exactly the kind of
unexamined default stacking real interaction work is supposed to catch.
One real limitation, noted rather than silently shipped: the overlay
anchors above the trigger with a fixed offset, not actual cursor-following
or viewport-edge detection — a severity glyph in the very first ledger row
could clip above the viewport. Not fixed now; flagging it here instead of
discovering it only when someone hits it.

**Next:** Phase 2.5 (confidence field + noise-textured value) as revised
after Phase 1, unchanged.

## Phase 2.5 — confidence field + noise-textured value

Add a `confidence` field to `Finding` (plausibly: mirrors
`PostureConfidence` from `../design/FEATURE-PLAN.md` —
`measured`/`untrusted-read`/`unmeasured` — since vuln_res findings already
carry a `source` field that implies a confidence tier:
`real-data-verification`/`fuzzer-confirmed` read as more certain than
`static-analysis`). Only once that exists does the noise-as-texture
treatment have something real to render instead of an invented value.

## Phase 2 — loupe tooltip + noise-textured value

Hover-driven, stateful. The loupe needs real interaction-timing decisions
(delay before showing, where it anchors); the noise-as-honesty texture
needs an actual visual treatment for `posture_confidence`/finding
`source`-derived uncertainty, which doesn't exist as data yet on this
view — may need to introduce a `confidence` field to `Finding` first rather
than inventing a visual with nothing to drive it.

## Phase 3 — scrub timeline

Replaces the static sweep-history `Rail` rows with a draggable control.
Saved for last because it's the most complex interaction (drag math,
re-rendering the ledger against historical sweep data that doesn't fully
exist as sample data yet — only `currentSweep` has full finding detail
today; `sweepHistory` is just id+count). Needs its own sample-data pass
before the component makes sense.

## Phase 4 — posture/evidence view

`BootState`/`PlannedTransition`/`Report` per `../design/FEATURE-PLAN.md`:
new `PostureConfidenceTick`, `SecurityModeTick`, invariants checklist,
carbon-copy diff row. Third dial position. Left for last because it's the
largest net-new surface, not an extension of what exists.
