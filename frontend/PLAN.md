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

## Phase 1 — stamp mark + phosphor trace (next)

The two lowest-risk, highest-payoff components from `../design/AESTHETIC.md`'s
catalog: a stamp mark for `fixed`/`disclosed-upstream` rows (static SVG/CSS,
no interaction, no state — purely visual, so it's a good next step after an
all-logic Phase 0) and a phosphor trace sparkline for sweep cadence in the
headline block (a drawn SVG line, not a filled bar/area per the aesthetic's
own rule). Both are presentational and testable by snapshotting their
generated path/attributes, not by simulating interaction.

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
