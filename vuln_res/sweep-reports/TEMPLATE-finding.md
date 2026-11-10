---
id: <sweep-id>/<slug>
target: <e.g. state::collect::collect>
source: static-analysis | fuzzer-confirmed | exploit-dev-chain
status: open | fixed | disclosed-upstream | false-positive | escalated-to-human
score: <reachability 1-3> x <memory-safety-weight 1-3> x <blast-radius 1-3> = <product>
discovered_by: <agent name>
sweep: ../INDEX.md#<sweep-id>
discovered_at: <YYYY-MM-DD>
---

## Short description

**Required for every finding, no exceptions — especially for anything `vulnres-exploit-dev`
produces (single-bug or multi-step chain).** 2-4 sentences, no jargon a non-specialist
couldn't follow: what's wrong, why it matters, roughly how bad.

## Technical detail

What crashes/hangs/misbehaves, and under what input or condition. For a `static-analysis`
source finding: the exact code pattern and why it's risky, with file:line references. For
a `fuzzer-confirmed` source finding: full classification detail per below.

## Reproduction

```
<exact repro command/steps. For a static finding this may just be "read <file>:<line>";
for a fuzzer-confirmed finding this must be a re-runnable command.>
```

PoC artifact (if any): `<path, e.g. ./<slug>.poc>` — per `../../CLAUDE.md`'s definition,
a minimal input/trigger against **our own code**, never anything aimed at Apple's
platform security.

## Classification

- **Type:** memory-safety | panic | hang | logic-divergence
- **Reachability:** <1-3> — is this called from a live CLI path today?
- **Blast radius:** <1-3> — does it feed a security-relevant decision (`SecurityMode`,
  `Environment`, a future `is_mutation_allowed()`), or is it cosmetic?

## Chaining notes (if applicable)

Does this compose with another open finding to demonstrate greater impact (Pwn2Own-style
bug chaining, scoped to our own code only)? Link the other finding and describe the
composition, or state explicitly that this was checked and nothing composes.

## Resolution

Fix PR link, upstream issue link, or the human escalation note and the decision that came
back. Filled in by `vulnres-disclosure`.
