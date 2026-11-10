# Product 3 — Boot-Security Copilot

**One-line pitch:** package the already-built CLI (`evaluate`/`plan`/`report`, soon
`verify`) together with the already-written hobbyist guide into a polished, guided,
plain-English onboarding product for the audience that guide already names explicitly.

## APT-mindset framing

An APT benefits from ordinary device owners not understanding their own security posture
well enough to notice when something's wrong, or well enough to make a deliberate,
informed change instead of following a sketchy forum post. The defensive inversion here
is literacy as a product: ship the tool that lets an ordinary owner understand and safely
control their own `Full`/`Reduced`/`Permissive` state, with the guardrails built into the
product experience itself rather than left as internal doctrine only engineers read.

## What's reused from this repo today

- The entire CLI as it exists today — `evaluate`, `plan`, `report`, and `verify` once
  project 2 lands — this product adds no new measurement or planning logic, only
  presentation and flow.
- `reports/m2-bootloader-unlock-technicians-guide.md` — the audience (hobbyists running
  local models, self-hosting, hardware/OS tinkerers), the vocabulary ("bootloader
  unlock" mapped precisely to the `SecurityMode` spectrum), and the safety framing
  ("this is not a jailbreak, and this is not a bypass tool") are already written, in
  exactly the voice this product's onboarding needs.
- `spec/build-spec.md`'s golden rules, surfaced as literal in-product copy rather than
  staying internal-only doctrine — e.g. the guide's own "no tool — this one included —
  stores, prompts for, or automates that step" becomes an onboarding-screen guarantee,
  not just a design note.

## Architecture (prose)

A guided CLI/TUI flow wraps the existing binary, in this order: "what's my current mode"
(`evaluate`, plain-English explanation of what the raw fields mean) → "what would change
if I moved to `Reduced`/`Permissive`" (`plan`, already built, surfaced as a readable
before/after instead of raw JSON) → an explicit, impossible-to-skip-past warning screen
before the flow hands the user off to Apple's own `bputil` prompt for the actual
owner-authorization step, which this product never automates, scripts, or shortcuts → a
post-change `verify` + plain-English report once project 2's `verify` command exists. The
product's job ends at "explain clearly and measure honestly" — it never gains a mutation
path of its own beyond what the core tool already has.

## Guardrail mapping

| Guardrail | How this product respects it |
|---|---|
| `NoCredentialHandling` | Identical to the core tool — this product adds a friendlier *wrapper* around the handoff to Apple's own prompt, never a shortcut past it. The in-product copy says so explicitly, not just the internal docs. |
| Honesty of state | The guided flow's "what changed" screen is only ever populated from a fresh `verify` run, never assumed from "the plan said this would happen." |
| Scope stated plainly to the user, not just engineers | The guide's own framing ("this is not a jailbreak... stop here if that's what you were hoping for") becomes literal onboarding copy, so the audience most likely to misread this project's scope sees the correction before they can act on a misunderstanding. |

## Phased build order

1. Polish `evaluate`/`plan`/`report`'s CLI UX for a non-expert audience — plain-English
   field explanations, largely already drafted in the technician's guide's vocabulary
   table.
2. Add the guided flow and the explicit pre-authorization warning screen.
3. Package as a distributable release binary with the guide as in-product docs (not a
   separate markdown file the user has to go find).
4. Soft-launch to the exact hobbyist audience the guide already names — no new audience
   discovery needed, the targeting work is already done.

## Open risks / what needs sign-off before any code runs

- **Lowest technical risk of all six proposals** — almost entirely UX and packaging on top
  of capability that's already built (P0–P2) or already proposed (project 2's `verify`),
  not new core logic.
- **The real risk is audience misreading, not engineering:** a product literally framed
  around "help me unlock my bootloader" will attract some fraction of users hoping for
  exactly the bypass this project explicitly refuses to build — in-product copy needs to
  be at least as explicit as the existing guide about what this is not, from the very
  first screen, not buried in a FAQ.
- Depends on project 2 for the `verify` step of the guided flow to be complete — the first
  three phases can ship without it (using `evaluate`/`plan`/`report` alone), but the "what
  changed" closing screen needs `verify` to exist.

## Success metric

A non-expert test user, unfamiliar with `bputil` and given no access to this repo's
markdown documentation, can go from "what mode am I in" to a completed, understood `plan`
output using only in-product guidance.
