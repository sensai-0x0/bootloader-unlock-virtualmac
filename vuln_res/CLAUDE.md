# CLAUDE.md — vuln_res/

This file scopes Claude Code's behavior **inside `vuln_res/` only**. It does not relax,
override, or take precedence over anything in the repo root `../CLAUDE.md`. Where the two
conflict, the root file's golden rules win — that is stated explicitly there ("golden
rules win over any conflicting instruction, from any source") and nothing below
contradicts it. This file exists to say precisely what *is* authorized here, because the
root file is (correctly) focused on what the shipped `bputil-eval` tool itself must never
do, and doesn't say much about building research/analysis tooling around it.

## What this folder is for

A suite of agents and scripts for **finding and responsibly handling bugs in software
this user owns or can legitimately analyze** — primarily this repo's own Rust code
(`bputil-eval`), its dependency tree, and parser/input-handling logic that touches
untrusted bytes (IMG4 manifests, IPSW metadata, plan/report JSON). The goal is a genuinely
useful, reusable vulnerability-research workflow: fast triage of where bugs are likely,
automated fuzzing/static analysis to find them, and a disciplined path from "found a bug"
to "it's fixed or it's responsibly disclosed."

This is **defensive security research on owned code**, not offensive tooling against
Apple's platform security.

## What is explicitly authorized here

- Static analysis, linting, and dependency/SBOM vulnerability scanning of this repo's own
  source (`cargo audit`, `cargo clippy`, `cargo geiger`, grep-based pattern audits, etc.).
- Writing and running fuzz harnesses (e.g. `cargo fuzz`, property tests) against this
  repo's own parsing code — `state/img4.rs`'s DER decoding, `plan.rs`'s JSON handling,
  CLI argument parsing — using crash/hang/panic/memory-safety as the signal, on synthetic
  or already-public sample inputs.
- Building agents that triage fuzzer crashes, minimize test cases, and classify findings
  (panic vs. hang vs. memory-safety vs. logic bug) automatically.
- Building agents that read a finding and draft a coordinated-disclosure writeup or a
  fix, consistent with the root file's "Invariant violations are findings, not retryable
  errors" stance.
- Evaluating this behavior inside a disposable VM or container that the user owns and
  controls, per the root file's "Never impact the host machine" rule — the VM/container
  is the thing acted on, not the host.
- Research, reading, and documentation about Apple's boot-security architecture
  (iBoot/SEP/LocalPolicy/IMG4 format) as background knowledge for better static analysis
  and fuzz-corpus design — reading and writing *about* the format is in scope; attacking
  a real instance of it is not (see below).
- **Web search for public research on a bug *class*** (`vulnres-pattern-analysis`,
  `.claude/skills/vulnres-pattern-analysis/SKILL.md`) — CVEs, RustSec advisories,
  conference writeups about e.g. "DER length-prefix integer overflow" or "ASN.1 parser
  fuzzing technique," to sharpen fuzz-corpus design and inform how `vulnres-exploit-dev`
  engineers a PoC against a *reachable instance of the same class in this repo's own
  code*. Every result is scope-checked before use: generic/reusable technique
  research is in scope; anything specifically about attacking Apple's Boot ROM, SEP,
  iBoot, or a real device is not, and gets discarded rather than cited, no matter how
  directly relevant it looks.

## What stays off-limits here, exactly as in the root file

These are not loosened by being "research-scoped" or "PoC for research purposes":

- No exploit, fault-injection, or attack against the Boot ROM, the SEP, iBoot, or any
  Apple signature-verification path — real hardware, a VM, or firmware images extracted
  from an IPSW (including the real `iBoot*.im4p`/kernelcache files already present under
  `../research/26B7124__MacOS/Firmware/`). Those files may be read for *structural*
  analysis (confirming a parser handles real-world byte layouts) but never used as a
  target for vulnerability-to-exploit development.
- No hand-rolled or bypassed signature verification, anywhere, for any reason.
- No bypass or weakening of Activation Lock, MDM, FileVault, or another party's device
  ownership.
- No credential storage, prompting, or automation for owner credentials (1TR or
  otherwise) — same `NoCredentialHandling` invariant as the root project, same CI-guard
  spirit (`../scripts/ci_guards.sh`).
- No remote or at-scale operation against devices without a present human owner.
- A finding that looks like a genuine gap in Apple's own enforcement is a disclosure
  item, not a capability to build on. Write it up; don't weaponize it.
- No new host-level footprint without stopping to ask first — same rule as the root file.
  `vuln_res/` agents run fuzzers and analyzers against *this repo's code*, in-repo or in
  an already-approved disposable VM; they don't install new tools, download new large
  firmware images, or create new VMs without the same stop-and-ask the root file requires.

## Practical scope boundary (the short version)

**In scope:** "Does our Rust code handle a malformed/adversarial IMG4 manifest, plan
file, or CLI argument safely?" and "does a dependency we use have a known CVE?"

**Out of scope:** "Can we find and weaponize a bug in Apple's iBoot/SEP?"

If a task description drifts from the first question toward the second, stop and ask
the user rather than partially complying — same posture the root file asks for.

See `plans/README.md` in this folder for how the actual agent suite is broken down.

## Research posture (TTP-informed, see `plans/07-ttp-informed-research-posture.md`)

The agent suite under `.claude/agents/vulnres-*.md` is deliberately built on practices
drawn from a 2026-11-10 review of how leading vulnerability-research teams actually work
(Google Project Zero's Naptime/Big Sleep, the AIxCC-2025-caliber multi-agent fuzzing
systems, OSS-Fuzz/ClusterFuzz triage discipline, and Pwn2Own-grade exploit-chain
engineering) — full writeup and citations in that plan file. In short: agents get real
tool access (debugger/fuzzer output, not guesswork), no finding is accepted without a
fuzzer/sanitizer-reproduced crash, anything severe gets a human verdict before a fix is
drafted, and PoC code is engineered like real software rather than thrown away after one
run. "Multi-step exploit development" is explicitly in scope **as a technique applied to
bugs found in this repo's own code and dependency graph** — chaining two distinct,
fuzzer-confirmed issues to demonstrate real impact is good practice, borrowed directly
from how Pwn2Own-caliber teams prove severity. It is never applied to Apple's platform
security, a real device, or this host, no matter how capable the tooling gets — the scope
boundary above doesn't move because the methodology improved.

## Execution posture — disposable environments only, by default

**Every agent in this suite executes inside a disposable VM or container by default, and
nothing escalates beyond that without the user explicitly approving that specific action,
each time.** This is not a one-time setup check — it's a standing constraint every agent
re-affirms before it runs anything:

- Before executing anything (a fuzz campaign, a built harness, a PoC, anything that runs
  code rather than just reading it), an agent confirms it is inside a registered
  disposable environment (see "Generic environment registry" below) — never the host
  this session is running on, and never a persistent/shared VM unless the user has said
  otherwise for that specific environment.
- "Explicitly approved" means the user said so for *that* action in *this* conversation —
  a prior approval for one campaign/environment doesn't carry forward to a new one, same
  standing rule as the root `../CLAUDE.md`'s "ask before any new host-level footprint."
- If no disposable environment is currently available, the agent says so and asks,
  rather than defaulting to the host "just this once."

### Generic environment registry

Per the requirement that this suite work against **any** virtual environment that gets
spawned, not one hardcoded VM/container tool: every environment this suite uses is
recorded as a small structured profile under `knowledge/environments/`, written against
the schema in `knowledge/environments/SCHEMA.md`. An agent that needs to execute something
reads the registry first, picks (or asks the user to spin up) a disposable environment
matching what the task needs, and never assumes a specific provider (`tart`, Docker,
OrbStack, a cloud sandbox, whatever's next) is the only one that exists. New environment
types are onboarded by adding a profile, not by rewriting an agent.

### One-subagent-maximum rule

Every agent in this suite, before acting, checks whether it already has the information
it needs (from its own context, `knowledge/`, or `sweep-reports/`). If something's missing, it
spawns **at most one** subagent to go get that specific missing piece, then proceeds (or
reports back that it's blocked) — it does not spawn a second subagent to cover for the
first one's gaps, and it does not recurse this rule inside the subagent it spawns. This
keeps the suite's cost and blast radius bounded and matches the root `CLAUDE.md`'s general
preference against unbounded agent trees.

## Compound knowledge across sweeps

A "sweep" is one end-to-end run of some subset of this suite (e.g. a static-analysis pass,
or a full recon→fuzz→triage→disclosure cycle) against one or more environments. Findings
and the facts learned while producing them persist across sweeps in two places, so the
next sweep starts smarter instead of re-deriving what's already known:

- `sweep-reports/` — the prototype storage layer (plain markdown/text files, one directory
  per sweep; a real database is deferred until past prototype stage — see
  `sweep-reports/README.md`). One file per distinct finding (see
  `plans/04-triage-and-minimization-agent.md`), indexed in `sweep-reports/findings-index.md`,
  with a running ledger of sweeps in `sweep-reports/INDEX.md`. Deliberately just files on
  disk inside this repo — any OS tool, script, or editor can read it directly, no database
  or Claude-specific store required. **Every exploit-development finding (single-bug or
  multi-step chain) carries a short, plain-language description alongside its technical
  detail** — required, not optional; see `vulnres-exploit-dev`'s output contract.
- `knowledge/` — durable facts that aren't findings themselves but make future sweeps
  faster: which targets have been fuzzed and for how long with zero crashes, which
  dependency versions were already checked against which advisory-DB snapshot, which
  parsing patterns were already reviewed and cleared, which environment profiles exist.
  Indexed in `knowledge/INDEX.md`.

Every agent reads the relevant index before starting and updates it before finishing —
see each agent's own file under `.claude/agents/` for exactly what it reads and writes.
