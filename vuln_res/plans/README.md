# vuln_res/plans/ — index

This folder breaks the vulnerability-research agent suite into independently buildable
pieces. Read `../CLAUDE.md` first — it's the scope contract every plan here operates
inside. Read `../AUDIT.md` second — it's the concrete findings in `bputil-eval`'s own code
that this suite is designed to have caught, and the seed corpus for the first fuzzing
campaign.

## Why an agent suite, and why this shape

A single "run a fuzzer" script finds crashes. It doesn't triage them, doesn't tell you
which one is worth a human's time first, doesn't minimize the reproducer, and doesn't
write the disclosure or the fix. The useful version of "vulnerability research" is a
pipeline, and a pipeline with distinct, narrow stages is exactly what a set of
specialized agents is good at — each one has a small, checkable job, and the handoffs
between them are the thing that makes the whole pipeline fast instead of a pile of raw
fuzzer output nobody reads.

```
 ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐
 │  01 Recon /  │──▶│ 02 Fuzz-Harness│──▶│ 03 Campaign        │
 │  Static+SBOM │   │    Agent       │   │    Orchestrator     │
 └──────────────┘   └────────────────┘   └─────────┬────────┘
                                                      │ crashes
                                                      ▼
                                           ┌────────────────────┐
                                           │ 04 Triage +         │
                                           │    Minimization     │
                                           └─────────┬──────────┘
                                                      │ minimized, deduped, scored
                                                      ▼
                                           ┌────────────────────┐
                                           │ 05 Fix / Disclosure │
                                           └────────────────────┘

        06 Sandboxed-VM evaluation runs underneath 02/03 as the execution
        environment, never the host — see that plan for why.
```

## The "quickly evaluating vulnerabilities" method

The fast-evaluation problem this suite is designed to solve: given a pile of fuzzer
crashes or a static-analysis report, which ones are worth a human's attention *first*?
The scoring rubric (full detail in `04-triage-and-minimization-agent.md`) is three
cheap-to-compute signals multiplied together, not a slow manual severity debate per bug:

1. **Reachability** — is the crashing function called from a production code path today
   (`state::collect`, `main.rs`'s CLI dispatch), or is it currently dead/test-only code
   (like `img4::parse_manifest_der` right now — see `AUDIT.md` §1.1)? Reachable now beats
   reachable later.
2. **Memory-safety weight** — a crash under ASan/a real segfault/an OOM outranks a clean
   `panic!`/`Result::Err`, which outranks a wrong-but-safe value. Rust's type system
   already prevents most of the worst outcomes; the ones that get through are the ones
   worth looking at first.
3. **Blast radius if wrong** — does the bug corrupt data that feeds a security *decision*
   (e.g. `SecurityMode`, `is_mutation_allowed()`) versus data that's cosmetic (a
   `Display` string)? A wrong `SecurityMode` is categorically worse than a wrong
   human-readable line in `--json` output, even if both come from the same kind of bug.

This triages a flood of fuzzer output down to "fix this today" vs. "backlog" in minutes,
not hours, and it's the thing an agent can compute automatically from a crash's stack
trace and the reachability graph — no human judgment call needed for the first pass.

## What "PoC" means in this suite

Every plan below that mentions a PoC means: **a minimal input file plus a one-line repro
command that makes this repo's own code panic, hang, or crash under a sanitizer** — e.g.
`cargo fuzz run img4_decode crash-<hash>` reproducing a panic in `parse_manifest_der`.
That's it. It never means a working exploit against Apple's boot chain, a real device, or
a real VM's SEP emulation — see `../CLAUDE.md`'s scope boundary. A crash PoC against our
own parser is standard, uncontroversial fuzzing practice (it's how you prove a bug exists
and hand a fix-author something concrete to work from); it just isn't firmware exploit
development, and this suite doesn't drift toward that even when a "real" fuzz corpus
(the firmware images under `../research/`) is sitting right there.

## Plan sequence

| Plan | Builds | Depends on |
|---|---|---|
| [`00-threat-model-and-scope.md`](./00-threat-model-and-scope.md) | Attack surface inventory, explicit in/out-of-scope target list | `../AUDIT.md` |
| [`01-static-analysis-and-dependency-agent.md`](./01-static-analysis-and-dependency-agent.md) | `cargo audit`/`clippy`/custom-lint agent, CI-guard hardening | 00 |
| [`02-fuzzing-harness-agent.md`](./02-fuzzing-harness-agent.md) | `cargo fuzz` targets for the parsers named in `AUDIT.md` §1 | 00 |
| [`03-sandboxed-execution-environment.md`](./03-sandboxed-execution-environment.md) | Where campaigns actually run (container/VM, never host) | 02 |
| [`04-triage-and-minimization-agent.md`](./04-triage-and-minimization-agent.md) | Crash dedup, scoring, minimization pipeline | 02, 03 |
| [`05-disclosure-and-fix-agent.md`](./05-disclosure-and-fix-agent.md) | Writeup/patch-draft agent, coordinated-disclosure template | 04 |
| [`06-orchestration-and-scheduling.md`](./06-orchestration-and-scheduling.md) | How the agents hand off to each other, CI integration, cadence | all above |

Build in order — each plan's "exit gate" is a prerequisite for the next, same spirit as
the root project's own phased delivery.

| [`07-ttp-informed-research-posture.md`](./07-ttp-informed-research-posture.md) | How leading vuln-research teams' actual practices get adopted (and where they don't), with citations | all above |

## Implementation status

The suite described above is now built, not just planned:

- **Agents:** `../../.claude/agents/vulnres-{recon,fuzz-harness,environment-runner,triage,exploit-dev,disclosure,orchestrator}.md`
  — one per stage, plus the orchestrator. **Native `subagent_type: "vulnres-*"`
  invocation does not currently work in this harness** (project-level `.claude/agents/`
  isn't discovered — confirmed bug, see `06-orchestration-and-scheduling.md`'s
  "How to actually invoke this suite today" for the working fallback and
  `../sweep-reports/2026-11-10-001-recon-verification/agent-registry-not-live-this-session.md`
  for the root cause). Use that fallback, not a direct `subagent_type` call, until it's
  fixed upstream.
- **Compound knowledge store:** `../knowledge/` (`INDEX.md` + `environments/` registry) —
  durable facts and registered disposable environments, read/written every sweep.
- **Sweep-reports store:** `../sweep-reports/` — the prototype flat-file storage for
  every sweep and every distinct, fuzzer-confirmed bug (`INDEX.md`, `findings-index.md`,
  `TEMPLATE-sweep.md`, `TEMPLATE-finding.md`, one directory per sweep). Plain markdown and
  text files on disk, inside this repo — readable by any OS tool without going through
  Claude; see `../sweep-reports/README.md`. A real database is deferred until past
  prototype stage.
- Nothing has executed yet — no fuzz target has been built, no environment has been
  created. The first real sweep is `vulnres-orchestrator`'s to run, starting with
  `vulnres-recon` per that agent's own "what a sweep is" logic.
