# CLAUDE.md — frontend/

Guidance specific to this directory. The root `CLAUDE.md` (bputil-eval's own
rules — golden rules, refusal conditions, "never impact the host machine")
still applies everywhere, including here. This file is additive, not a
replacement.

## What this is

A dashboard for `vuln_res/` (the vulnerability-research/exploit-dev pipeline
that hunts bugs in bputil-eval's own code — never Apple's platform), and
eventually for bputil-eval's own evaluator contracts
(`spec/contract-spec.md`). It renders the "neuropunk paper" design system
defined in `../design/` (`AESTHETIC.md`, `components.md`, `FEATURE-PLAN.md`)
as a real, interactive React app. `../design/*.html` remain the static
reference mockups — this app is the implementation, and the two are kept in
sync by hand, not generated from one another.

**All data in this app is illustrative sample data** (`src/data/`) until a
separate decision is made to wire it to the real `vuln_res/` findings store
or to bputil-eval's own CLI output. Nothing here reads or writes repo files
at runtime.

## Stack — and why it's not the obvious choice

- **Bun, not Node.** Per the user's global instruction: bun is the package
  manager everywhere in this workspace.
- **Bun's own bundler/dev-server, not Vite.** `server.ts` serves
  `index.html` as a native Bun HTML import (`Bun.serve({ routes: { "/*":
  index } })`); `bun build ./index.html` produces the production bundle.
  This matches the convention already established in this meta-repo's
  `metacogna-rag` project ("HTML imports fully supported — no need for Vite
  in production"). Don't add Vite, webpack, or a CRA-style scaffold here.
- **Plain CSS custom properties, not Tailwind.** The whole point of the
  design system in `../design/` is a handmade token system answering to a
  specific brief (`../design/AESTHETIC.md`) — a utility framework's default
  spacing/color scale would fight that, not serve it. Every component owns
  one small co-located `.css` file; `src/styles/tokens.css` is the only
  shared stylesheet, and it exists to be the single place the palette and
  type scale are defined.
- **No React Router.** Two (soon more) views don't need a routing library;
  `src/router.tsx` is ~30 lines of `pushState`/`popstate` glue. Don't add
  one unless the view count or nesting genuinely outgrows this.
- **`bun test`, not Jest/Vitest.** Bun's built-in runner, with
  `@happy-dom/global-registrator` (see `bunfig.toml` → `happydom.ts`) for a
  DOM, and `@testing-library/react` for render/query helpers.

## Conventions

- **One component, one file, one co-located stylesheet.** `Foo.tsx` +
  `Foo.css`, imported directly (`import "./Foo.css"`) — Bun's bundler
  inlines it. Keep components small; if a file is doing two jobs, split it.
- **No `<button>`, ever, on this surface.** Every interaction is a native
  disclosure (`<details>`/`<summary>`, via `Ledger`/`LedgerRow`), a native
  checkbox styled as a toggle (`Legend`), or an anchor styled to not look
  like one (`Dial`). This isn't just the aesthetic (`../design/AESTHETIC.md`
  — "no buttons" as a punk refusal) — once this app grows a view onto
  bputil-eval's own `PlannedTransition`/`apply`/`revert` contracts
  (`../design/FEATURE-PLAN.md`), it becomes a hard requirement:
  `ReadOnlyUnlessGated` means no control here may ever be capable of
  triggering a mutation. Don't add one "temporarily."
- **Pure functions for anything that isn't markup.** Score math
  (`src/lib/score.ts`), filtering (`src/lib/filter.ts`) — no mutation, easy
  to unit test, tested. New display logic beyond trivial JSX conditionals
  belongs in `src/lib/`, with a test, not inlined in a component.
- **Sample data lives in `src/data/`, typed by `src/data/types.ts`.** If/when
  this wires to a real source, add a validation boundary there (the
  project's TypeScript rules call for Zod at system boundaries) — don't
  trust an external payload to already match these types.

## Commands

```bash
bun install        # install dependencies
bun run dev         # dev server with hot reload, http://localhost:5173
bun run build       # production bundle -> dist/
bun test            # unit + component tests
bun run typecheck   # tsc -b --noEmit
```

## Before marking any UI work done here

No headless browser is available in this environment without installing
one on the host, which the root `CLAUDE.md`'s "never impact the host
machine" rule means asking about first — don't just install Playwright/
Puppeteer browser binaries to get a screenshot. Verify instead with: `bun
test` (behavior), `bun run typecheck` (types), `bun run build` (it actually
bundles), and a manual contrast check against `src/styles/tokens.css`'s hex
values for any new color pairing (see the computation already done for
`signal-green-muted` vs `signal-green-dim` as a worked example). Say
explicitly if a change hasn't been visually verified in a real browser,
rather than implying it has.
