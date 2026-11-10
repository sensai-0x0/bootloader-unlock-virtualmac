# Product 2 — Vulnerability-Triage-as-a-Service

**One-line pitch:** offer the proven recon + triage scoring pipeline — already used to
find and fix two real bugs in this repo's own code — to other owners of Rust/parser-heavy
codebases who want the same fast "which bug deserves a human's time first" answer.

## APT-mindset framing

An APT benefits from defenders being slow and undiscriminating about which of a pile of
fuzzer crashes or static findings to look at first — triage fatigue is a gift to an
attacker racing to weaponize something before it's noticed. The defensive inversion is
to sell the thing that makes defenders fast and discriminating: the
reachability × memory-safety-weight × blast-radius scoring rubric this suite already
uses internally, generalized past this one repo.

## What's reused from this repo today

- `.claude/agents/vulnres-recon.md`'s `contains()`-pattern lint methodology — a concrete,
  reusable technique (trace every risky string-match call site feeding a security
  decision, flag the ones with no fail-closed branch) that has already caught two real
  bugs here (`ssv-enabled-contains-whole-blob`, `security-mode-full-contains-whole-blob`),
  not a hypothetical capability.
- `.claude/agents/vulnres-triage.md`'s scoring rubric (`vuln_res/plans/04-triage-and-minimization-agent.md`)
  — proven, not just designed.
- `vuln_res/sweep-reports/TEMPLATE-finding.md` / `TEMPLATE-sweep.md` — the output shape
  customers would receive, already battle-tested on this repo's own sweeps.
- `vulnres-pattern-analysis` (skill) — cross-sweep pattern detection plus public-technique
  lookup for the *same bug class*, which generalizes naturally to "has this class of bug
  shown up in other codebases this service has reviewed."

## Architecture (prose)

A customer brings their own repository and, for the fuzzing half of the pipeline, their
own crash artifacts or corpus — this product **never executes customer code** without the
exact same disposable-sandbox discipline this project already requires for itself
(`vulnres-environment-runner`'s rules, unchanged, just applied to a new codebase). Recon
and triage agents run against the submitted code, produce scored, templated findings in
the same shape this repo's own sweeps already use, and hand them back. Disclosure —
whether and how to fix, file upstream, or escalate — stays entirely the customer's own
call; this product's output contract ends at "here's what's wrong and how urgent it is,"
mirroring `vulnres-recon`'s own boundary ("you find and classify; you don't fix or
weaponize").

## Guardrail mapping

| Guardrail | How this product respects it |
|---|---|
| Defensive research on owned/authorized code only | Extended contractually: every customer must attest ownership or legitimate authorization for whatever repo they submit, before any analysis begins — this is a hard intake gate, not a formality, and mirrors the root project's own "owned device only" golden rule applied to code instead of hardware. |
| Exploit-dev stays bounded | If a submitted, confirmed crash needs impact-escalation, this product applies the exact same bound `vulnres-exploit-dev` already enforces on this repo — proving a bug's reach within the customer's own binary/process, never anything resembling privilege escalation against a host or device. |
| No execution outside a sandbox | Customer code runs under the same `vulnres-environment-runner` discipline as this repo's own fuzz targets — disposable, resource-capped, network-isolated, every time, regardless of how routine a repeat customer's submissions start to feel. |
| Scope stays on what's submitted | This product never goes looking beyond what a customer explicitly provides — no "let's also check your dependencies' dependencies" without separately asking, same spirit as this suite's own one-subagent-maximum discipline against scope creep. |

## Phased build order

1. Generalize the recon/triage agent prompts beyond `bputil-eval`-specific paths — today
   they reference `state/img4.rs`, `cmd_verify`, and this repo's specific `contains()`
   call sites by name; a real product needs the methodology extracted from the
   repo-specific instances.
2. Pilot on one or two other owned/authorized repos (e.g. this user's other Metacogna
   projects) to prove the generalization actually holds, not just that it reads well.
3. Formalize the customer-ownership-attestation intake step as an explicit, auditable gate
   — not an assumption baked into the agent prompts.
4. Packaging/pricing — explicitly deferred past proving the pipeline generalizes.

## Open risks / what needs sign-off before any code runs

- **The biggest risk is scope creep into analyzing a repo without real authorization** —
  the ownership-attestation step must be a hard, logged gate from day one of the pilot,
  not something added after a pilot customer is already found.
- Generalizing agent prompts away from this specific codebase's exact file paths and
  patterns is real engineering work, not a rename — the `contains()` lint in particular is
  currently written against three named, specific call sites in this repo.
- Any pilot repo chosen for step 2 needs the same explicit ownership confirmation this
  product would later require of a paying customer — "it's this user's own other project"
  should still be stated and confirmed, not assumed from context.

## Success metric

The generalized pipeline successfully triages and scores a seeded, known bug in a
**second, non-`bputil-eval`** owned Rust codebase, using the same scoring rubric, with no
`bputil-eval`-specific assumption (a hardcoded file path, a specific `SecurityMode`-shaped
field name) leaking through into the result.
