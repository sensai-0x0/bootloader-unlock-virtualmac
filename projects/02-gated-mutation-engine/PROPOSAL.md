# Project 2 — Gated Mutation Engine (building out P3)

**One-line pitch:** implement the still-stubbed `authorize`/`execute`/`verify.assert_invariants`
pipeline now that the disposable-VM round trip (M8/M9/M10) proved `bputil`'s mutation path
is measurable and reversible — turning "a human typed `bputil` live, by hand" into a
reviewed, tested, gated tool, with the human still required for exactly the one step
golden rule 4 reserves for them, forever.

## APT-mindset framing

An APT wants automated, silent, unattended security-state changes at scale, with no
owner friction and no record. The defensive inversion is specific, not generic: build
*everything around* the owner-authorization step to be fast, correct, and
auditable — plan validation, pre-flight checks, exact-argv enforcement, fresh
post-mutation measurement, evidence bundling, rollback — while making the
owner-authorization step itself **more** deliberate than hand-typed `bputil` currently is,
never less. The thing this project automates is the scaffolding around the human, not the
human's own moment of authority.

## What's reused from this repo today

- `spec/contract-spec.md`'s already-written pre/postconditions for `authorize`, `execute`,
  and `verify.assert_invariants` (lines ~150–180) — the contract exists; only the
  implementation is missing.
- `plan.rs`'s command generation — already confirmed correct against real hardware: the
  M8–M10 log entries in `progress/milestones.md` note explicitly that the hand-typed
  `bputil` commands the user ran "match `plan.rs`'s own committed golden file... exactly."
- The M8–M10 evidence itself — `evidence/vm-sec-research-25D125/*.json` is real
  before/after `BootState` data from an actual `Reduced → Permissive` transition, usable
  as an offline test fixture for `verify.assert_invariants` without needing a live VM for
  every test run.
- `report.rs`'s hash-chained bundle format — already the output contract `verify` needs to
  produce.
- `wrapper.rs` — the one place any subprocess call is allowed to originate; `execute.rs`
  has nowhere else to go.

## Architecture (prose)

`authorize.rs` checks `env::is_mutation_allowed()` (environment must be `OneTrueRecovery`)
and gates on a live, typed owner confirmation — never stores, prompts for, or automates
the OS-level credential itself; that stays Apple's own `bputil` prompt, entirely outside
this code path, exactly as it is today. `execute.rs` takes the already-generated
`PlannedTransition` and runs **only** its exact `argv` through `wrapper.rs` — never
freeform, never reconstructed from user input at execute time, so there is no path from
"the plan said X" to "the tool did Y." `verify.rs`'s `assert_invariants` is a pure
function of `(baseline, fresh)` — it needs no live system to test, which is exactly why
the M8–M10 fixtures make steps 1–2 below testable without hardware at all.

## Guardrail mapping

| Contract-spec invariant / golden rule | How this project enforces it |
|---|---|
| `ReadOnlyUnlessGated` | `execute.rs` only ever runs after `authorize.rs` confirms 1TR + live confirmation — no code path reaches `wrapper.rs`'s mutating commands otherwise. |
| `SingleContainerTouched` | `execute.rs`'s argv comes from one `PlannedTransition` targeting one named volume group; nothing broader is ever constructed. |
| `NoCredentialHandling` | Owner credential entry stays entirely inside Apple's own `bputil` prompt — this project adds zero new surface area that could store, log, or forward it. |
| Golden rule 7 (invariant violation = halt, never retry) | `verify.assert_invariants` returning any `held == false` is exit 13, full stop — `execute.rs` never loops back and retries a mutation based on a failed verification. |
| Golden rule 8 (honesty of state) | `execute.rs` never reports success from `bputil`'s own exit code alone — only `verify.rs`'s fresh post-mutation `BootState` can close out a session, same discipline the M6 log entry called out explicitly ("`bputil`'s own success message is not itself the evidence this project requires"). |
| Reversible | Every `TargetProfile` this engine can reach already has a committed revert path in `plan.rs`'s golden files — `execute.rs` doesn't add a profile without one. |

## Phased build order

1. **`execute.rs`, offline:** implement argv-matches-plan enforcement; unit test against
   `plan.rs`'s existing golden-file plans. No real execution yet — this step is pure Rust
   logic and fixture comparison.
2. **`verify.rs`, offline:** implement `assert_invariants` as a pure function; unit test
   exhaustively against the M8–M10 evidence bundle's real before/after JSON (already
   committed to this repo) plus deliberately-broken synthetic fixtures for each invariant.
   This step can reach high confidence without touching any hardware at all.
3. **`authorize.rs`:** implement the 1TR-gate check and the human-confirmation flow.
   Testable against `env::detect()`'s existing logic and synthetic environment states; the
   live-confirmation UX itself needs a human to actually try it, which is step 4.
4. **First real round trip:** against a fresh disposable VM, human owner physically
   present and typing their own credentials at `bputil`'s own prompt — this is
   `spec/phased-plan.md`'s existing P3 exit gate (`full → reduced → full`), unchanged by
   this proposal, just finally attempted with the real tool instead of hand-typed `bputil`.

## Open risks / what needs sign-off before any code runs

- **Steps 1–2 can be built and tested entirely offline** against already-committed
  fixtures — this is genuinely safe for autonomous work, unlike the rest of this
  portfolio's execution-touching proposals.
- **Step 4 is explicitly the boundary `CLAUDE.md`'s "Repository status" section already
  names** as needing "a human with physical hardware access driving it" — this proposal
  does not reinterpret that boundary; it just gets the codebase ready so that when the
  user is present for step 4, there's a real, tested tool to run instead of hand-typed
  commands.
- A bug in `execute.rs` that silently diverges from the plan is the single
  highest-consequence bug class in this entire codebase — it feeds directly into golden
  rule 2 (supported mechanisms only). Test coverage for step 1 should be treated as
  non-negotiable before step 4 is attempted, not best-effort.
- This project should not be started as "finish P3 autonomously" — the existing
  `CLAUDE.md` boundary on why P3 was left unstarted still applies to steps 1–3's *design*
  decisions, even though their *testing* can happen offline; the user should review the
  implementation before step 4, not just before running it.

## Success metric

`cargo test` is green for steps 1–2, using the already-committed M8–M10 evidence as
fixtures (no live target needed to prove this much) — **plus** one real step-4 round trip
against a fresh VM, human physically present, matching `spec/phased-plan.md`'s P3 exit
gate (`full → reduced → full`) verbatim, run by the actual `bputil-eval` binary end to
end, not assembled from separately-run commands the way M10's `Permissive` proof was.
