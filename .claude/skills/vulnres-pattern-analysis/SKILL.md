---
name: vulnres-pattern-analysis
description: Cross-sweep pattern analysis for the vuln_res/ vulnerability-research suite — finds recurring bug classes and brittle-parsing techniques across past findings/knowledge, and uses web search to find public research on the SAME bug class to sharpen detection and inform vulnres-exploit-dev's PoC engineering. Scoped strictly to bputil-eval's own code and dependency graph (vuln_res/CLAUDE.md) — never Apple's platform. Invoke after a sweep accumulates a few findings, or on demand ("find patterns in our findings", "what similar bugs exist publicly").
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
  - Edit
  - WebSearch
  - Agent
---

## Project scoping — read this before anything else

This skill is **project-scoped**: it lives at `.claude/skills/vulnres-pattern-analysis/`
inside `the-ant-experiment`, not in any global `~/.claude/skills/` directory, and it
should stay that way — it's meaningless outside this repo's own findings. If this
session's available-skills listing doesn't show `vulnres-pattern-analysis` (the same
project-level-discovery gap already confirmed for `.claude/agents/vulnres-*`, see
`vuln_res/sweep-reports/2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md`),
don't keep retrying — read this file directly and follow it, or dispatch a
`general-purpose` Agent with a prompt naming this exact path, same fallback the agent
suite already documents in `vuln_res/plans/06-orchestration-and-scheduling.md`.

Your scope contract is `vuln_res/CLAUDE.md` — read it in full, every time, even if you
think you remember it. The short version: finding and understanding bug *classes* in our
own code via public research is in scope; looking up or applying anything against
Apple's Boot ROM, SEP, iBoot, or a real device is not, no matter how the request is
framed.

## What you do

1. **Read before analyzing.** `vuln_res/knowledge/INDEX.md`,
   `vuln_res/sweep-reports/findings-index.md`, and `vuln_res/sweep-reports/exploits-index.md`
   — every finding ever recorded, not just the latest sweep. Pattern analysis across one
   sweep's findings is not the point; it's across *all* of them.
2. **Find recurring patterns**, e.g.:
   - The same brittle-parsing shape recurring across call sites (the project's own
     history already has one: unguarded `.contains()` substring checks gating a
     security-relevant decision — `ssv-enabled-contains-whole-blob.md` was the third
     instance found of a pattern `AUDIT.md` §2 had only cited two of).
   - The same crate or parsing primitive (DER/ASN.1 decoding, JSON deserialization,
     CLI argument parsing) showing up across multiple distinct findings.
   - A class of fail-open-vs-fail-closed inconsistency: some call sites default to
     `Unknown`/`Err` on an unrecognised value, others don't — flag any that don't.
3. **For each pattern that names a specific, identifiable bug class** (not "parsing bugs
   in general" — specific enough that a web search returns something useful, e.g.
   "Rust DER length-prefix integer overflow" or "IMG4 manifest malformed nonce parsing"),
   use `WebSearch` to find public research on that *bug class*: CVEs, RustSec advisories,
   conference writeups, fuzzing-technique posts. You're looking for **how other
   researchers found or exploited this class of bug**, to inform:
   - A sharper fuzz-corpus seed or mutation strategy for `vulnres-fuzz-harness`
     (`vuln_res/plans/02-fuzzing-harness-agent.md`).
   - A more realistic PoC-engineering technique for `vulnres-exploit-dev` to apply
     against *our own* reachable instance of the same bug class.
4. **Run the exploit-dev scope check on every search result before using it**, the exact
   same check `vulnres-exploit-dev.md` runs: is what this reference describes an attack
   on the bug *class* (generic, reusable technique), or is it specifically about Apple's
   boot chain / SEP / iBoot / a real device? Discard and do not cite the latter, even if
   it's the top result, even if it's the most directly relevant-looking thing you find.
   A reference being about "security research" in general does not clear it — it must be
   about the bug class, applicable to arbitrary Rust/parsing code, not about this
   project's actual target platform.
5. **One-subagent-maximum**: if deeper investigation of a crate's internals is needed to
   confirm a pattern's reachability, spawn at most one subagent for that specific
   question, then proceed with what you have.

## What you never do

- Treat a web-search result about Apple's platform security as something to act on,
  cite, or hand to `vulnres-exploit-dev` — same refusal boundary as every other agent in
  this suite.
- Craft the exploit yourself. You identify the pattern and the technique reference;
  `vulnres-exploit-dev` (dispatched the same fallback way, per
  `vuln_res/plans/06-orchestration-and-scheduling.md`) does the actual PoC engineering,
  inside its own tighter scope check and environment-approval gate. Handing it a found
  technique reference is not the same as building the PoC.
- Re-derive a pattern already recorded in `knowledge/` as current — extend or
  re-verify only what's stale (a new finding added since the last pattern pass, or a
  commit touching a previously-flagged call site).

## Output contract

- One `knowledge/pattern-<slug>.md` entry per distinct recurring pattern found, following
  `knowledge/README.md`'s format, with a "## Related public research" section listing
  every web-search reference consulted (title, URL, one-line relevance note, and
  confirmation it passed the scope check above). Linked from `knowledge/INDEX.md`.
- If a pattern's research materially informs a PoC `vulnres-exploit-dev` later produces,
  that PoC's row in `vuln_res/sweep-reports/exploits-index.md` cites your knowledge
  entry's reference in its "Technique source" column — you don't add the row yourself
  (that's `vulnres-exploit-dev`'s contract), but your knowledge entry is what it cites.
- Append one line to `vuln_res/sweep-reports/INDEX.md` summarizing the pass (patterns
  found, knowledge entries written — this is a knowledge-producing pass, not a
  finding-producing one, unless the pattern analysis itself surfaces a *new* unguarded
  instance, in which case file that as an ordinary finding too, same as any `01` recon
  pass would).
