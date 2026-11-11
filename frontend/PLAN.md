# Build plan — vulnres-dashboard

Tracks phases, what shipped, and what the next phase should be revised
because of what the last one taught. Updated at the end of every work
block, not drafted once up front and left stale.

## Cross-cutting — responsive pass (done)

Not a phase, a correctness pass across all five: `#root` had a fixed
`max-width: 920px` — centered, but never actually stretching with the
viewport. Fixed:

- `#root`: fluid `width: 100%` up to a `max-width: 1400px` cap (wide
  enough to use a large monitor, capped so a ledger row doesn't become a
  150-character line), side/vertical padding via `clamp()` instead of a
  single breakpoint jump.
- `--text-headline`: `clamp(40px, 9vw, 64px)` instead of a fixed size plus
  one media-query override.
- `Dial`, `InvariantsChecklist`'s row: added `flex-wrap: wrap` — three nav
  items and a long invariant name next to a tick were both one
  narrow-viewport away from forcing horizontal overflow, not because
  anything was broken today, but because nothing stopped it from breaking
  the next time a label got longer.
- `Ledger`'s four/five-fractional-column grids: a real mobile fix, not
  just a fluid tweak — fractional columns still squeeze a description down
  to a few characters per row on a phone. Added a `max-width: 640px` rule
  that stacks each row's columns to one per line instead.
- `PhosphorTrace`: dropped the fixed SVG `width`/`height` attributes in
  favor of a CSS-driven size (`width: 100%` up to a small cap, fixed
  height) — it was rendering at the same 120px box on a 4K monitor as on a
  phone.
- `overflow-x: hidden` on `body` as a defensive backstop, not a fix for
  anything specific found.

**Verified:** `bun run typecheck` clean, `bun test` 54/54 (unchanged —
this was a presentation pass, no logic changed, so no new tests), `bun run
build` bundles clean, confirmed via a dev-server fetch that the new rules
are actually present in the served CSS (checked directly — Bun's dev
server splits per-component CSS into separately hashed asset files rather
than serving the source paths, so a direct curl to `/src/styles/global.css`
returns nothing; fetched every served asset and grepped them instead).

**Not verified:** actual rendering at different viewport widths. No
headless browser is available in this environment without installing one
on the host, which this repo's own rules say to ask about first — said so
explicitly rather than claiming a visual check that didn't happen.

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

## Phase 2.5 — confidence field + noise-textured value (done)

**Shipped:** `FindingConfidence` (`measured`/`untrusted-read`/`unmeasured`,
mirroring `PostureConfidence` from `../design/FEATURE-PLAN.md`) added to
`Finding`, with each sample finding's tier derived from its actual
`status`/`reproduction` rather than assigned arbitrarily — the one finding
with `status: "open"` and no `reproduction` constructed yet is the one
marked `untrusted-read`; the three with a reproduction or a fix verified
are `measured`. `ConfidenceText` renders the degradation (`../../design/AESTHETIC.md`'s
"signal noise as honesty" — a measured value gets no wrapper at all, the
honest default is to add nothing). Wired into both the finding row's
target text and, more interestingly, into `SeverityGlyph` — which now also
degrades the loupe's *revealed* value, not just the inline glyph. That's
the "degrade on distrust" interaction rule from `AESTHETIC.md` actually
realized: a low-confidence value's loupe shouldn't hand back crisp false
precision.

**Verified:** `bun run typecheck` clean, `bun test` — 32/32 pass (5 new:
`ConfidenceText.test.tsx`, two added `SeverityGlyph` cases for the
default-measured and degraded-loupe paths), `bun run build` bundles clean
(7.94 KB CSS).

**Judgment / flagged, not fixed:** the `unmeasured` tier's color
(`--hairline-strong`) is already low-contrast at full opacity (checked
earlier against `graphite-900`, well under WCAG AA) and this phase makes it
dimmer still via `opacity: 0.7`. Unused in today's sample data — no
finding actually carries `unmeasured` — so it's dead code for now, not a
live accessibility bug, but it would be one the moment it's used for
anything the word itself doesn't already say. Worth a real color (not just
an opacity drop) before `unmeasured` ever appears in real data, rather than
assuming "it's supposed to look hard to read" excuses it.

## Phase 3 — scrub timeline (done)

**Shipped:** `ScrubTimeline`, built on a native `<input type="range">`
rather than hand-rolled pointer-drag math — full keyboard and touch support
for free, heavily restyled so it doesn't look like a default slider. Tick
labels underneath are a pointer-only shortcut layered on top of the
already-fully-accessible range input, not the sole way to operate it.
Required a real data-model fix first: `sampleSweep.ts`'s two historical
sweeps only had an `id` + a `fixedCount` scalar, which can't drive a real
ledger view. Gave both sweeps actual `Finding[]` — and in doing so, caught
and fixed a second ported-from-the-static-mockup inconsistency: the old
mockup's `currentSweep` included a finding (`ssv-enabled-contains-whole-blob`)
whose own id prefix (`2026-11-10-001/...`) said it was discovered in an
*earlier* sweep, not the current one. Moved it to where it actually
belongs. `sweeps` is now the single array both the trace and the scrubber
read, chronological, no more `.reverse()` needed anywhere.

**Verified:** `bun run typecheck` clean, `bun test` — 36/36 pass (4 new:
`ScrubTimeline.test.tsx` — range bounds, drag reports the new index, tick
click jumps directly, exactly one tick marked active), `bun run build`
bundles clean (9.0 KB CSS).

**Judgment:** choosing a native range input over hand-rolled drag math was
the right call for the same reason `Legend`'s checkboxes and `Ledger`'s
`<details>` were — every one of this app's "custom" interactions is a
native control wearing different clothes, not a reimplementation of
browser behavior. The real work this phase did was the data-model fix, not
the component; the component itself was close to free once the data was
honest.

## Phase 4 — posture view (done; split further than planned)

**Revised before starting:** the original Phase 4 bundled `BootState`,
`PlannedTransition`, and `Report` into one phase — exactly the "too large
to judge honestly before committing" mistake the Phase 0 retrospective
already named once. Split it: this phase ships only the `BootState`
posture ledger; `PlannedTransition`/`Report` (mode-transition rail, plan
preview, evidence/diff viewer, invariants checklist) move to Phase 5.

**Shipped:** `PostureConfidenceTick` and `SecurityModeTick` (both reuse the
filled/outline/dash tick grammar `StatusTick` established, each with their
own small dedicated stylesheet rather than forcing a shared component
across incompatible types). `PostureView` — a manifest-style header
(capture time, environment, host, confidence) plus a `boot-objects`-variant
ledger: one row for the target container's booleans, one row per enrolled
boot object, one per other container. Third dial position, `/posture`.
`sampleBootState`/`sampleBootStateUnmeasured` added, shaped to
`spec/contract-spec.md`'s actual `BootState` contract.

**The enrolled-object hashes are the first genuinely truncated value in
this app:** every earlier `Loupe` use (the severity glyph) showed the same
information twice, compact and magnified. Here, the collapsed row
literally cannot show a 96-character sha384 and stay a ledger; `Loupe`
shows the first 8 characters inline and the full hash on hover/focus. This
is the case `../design/AESTHETIC.md`'s loupe description was actually
written for.

**Verified:** `bun run typecheck` clean (after widening `Ledger`'s
`variant` prop type — `"findings" | "exploits"` wasn't open to a third
kind, a real gap caught by the compiler, not by inspection), `bun test` —
40/40 pass (7 new across `SecurityModeTick`, `PostureConfidenceTick`, and
`App.test.tsx`'s third-dial-position case), `bun run build` bundles clean
(10.19 KB CSS), dev server smoke-tested on `/posture` via `curl`.

**Judgment:** keeping `Reduced`/`Permissive`/`Unknown` visually identical
in `SecurityModeTick` (all neutral dash, word-only distinction) was a
direct application of the plan already written in
`../design/FEATURE-PLAN.md` before any code existed — a rare case where
the up-front contract mapping made the component a transcription, not a
decision. No new judgment call needed, which is itself worth noting: the
earlier planning work paid for itself here.

## Phase 5 — plan preview + evidence/report viewer (done)

**Shipped:** `PlannedTransition`, `Report`, `InvariantName` (the exact
eight invariants from `spec/contract-spec.md`), `DiffEntry` added to
`types.ts`. `PlanPreview` (mode-transition rail + a read-only plan row,
the human-gate tick borrowing `StatusTick`'s `escalated-to-human` look via
its new `label` override). `InvariantsChecklist` (held/violated, same
borrowed grammar — held is `open`'s green, violated is the amber triangle,
because contract-spec.md's own words for a violation are "routes the
finding to coordinated disclosure," i.e. exactly what escalated-to-human
already means everywhere else in this app). `CarbonCopyDiffRow`/`DiffLedger`
(struck-through old value, fresh new value — "the carbon copy" from
`../design/AESTHETIC.md`, not a before/after table). `samplePlan.ts`,
`sampleReport.ts` — the report sample deliberately carries one *violated*
invariant (`SingleContainerTouched`) rather than a clean verify, because
that's the case this component exists to render correctly, not the common
one.

**Reused rather than rebuilt:** generalized `StageRule` to take a `stages`
prop (it was hardcoded to vuln_res's six pipeline stages) so the same
component now also draws the `Full`/`ReducedKexts`/`PermissiveCustomKernel`
rail — one component, two unrelated domains, zero new CSS. Added
`securityModeAsProfileLabel` (tested) so an `Unknown` origin never lights a
guessed stage. All three new sections live on the existing `/posture`
view rather than new dial positions — current state, proposed plan, and
past verification are one device's continuous story, read top to bottom
like a ledger, not three separate tabs.

**Verified:** `bun run typecheck` clean, `bun test` — 54/54 pass (14 new),
`bun run build` bundles clean (11.28 KB CSS), `/posture` smoke-tested via
curl.

**Judgment — one real bug caught before it shipped:** reused
`.agents-run` for the evidence-bundle-path line without noticing its CSS
is scoped `.manifest .agents-run`, not a bare class — it would have
rendered completely unstyled outside a `.manifest` ancestor. Added a
proper shared `.meta-line` class instead of reaching for an inline style
override, which would have fixed the symptom without fixing the actual
scoping mistake for the next person who reuses `.agents-run` the same way.

**Status:** this closes every feature `../design/FEATURE-PLAN.md` scoped.
Still not done, by design: wiring any of this to a real `vuln_res/` or
bputil-eval data source, and the deferred items already flagged along the
way (the loupe's viewport-edge clipping, the `unmeasured` tier's contrast).
