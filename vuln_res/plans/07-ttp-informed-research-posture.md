# 07 — TTP-informed research posture

What leading vulnerability-research teams actually do differently from "run a fuzzer and
read the output," per a web-research pass (2026-11-10), and exactly how each practice gets
adopted into this suite — or explicitly doesn't, where it would cross `../CLAUDE.md`'s
scope line. See "Sources" at the end for everything cited here.

## 1. Tool-equipped agents, not bare-LLM judgment (Google Project Zero's Naptime/Big Sleep)

Project Zero's Naptime framework's key design choice is giving the model the *same tools*
a human researcher would use — a debugger, a scripting/REPL environment — rather than
asking it to reason about code in the abstract, and letting it explore multiple hypotheses
with the ability to recognize when it's stalled and stop.

**Adopted as:** every agent in `.claude/agents/vulnres-*.md` gets explicit tool access to
the actual artifacts (the real `cargo fuzz`/ASan output, the real stack trace, the real
binary under a debugger inside the sandbox) rather than being asked to guess at a bug's
shape from reading source alone. The "stop when stalled" behavior is encoded directly as
this suite's **one-subagent-maximum rule** (see `../CLAUDE.md`): an agent that doesn't have
what it needs spawns exactly one subagent to go get it, then proceeds or reports it's
blocked — it does not spiral into an open-ended subagent tree.

## 2. Every finding must be fuzzer/sanitizer-confirmed, never LLM-asserted (FuzzingBrain V2, AIxCC 2025, PBFuzz)

The multi-agent systems that performed well in DARPA's AIxCC 2025 competition share one
load-bearing design constraint: an LLM proposing "this looks like a bug" is not a finding
— it's a hypothesis, and the system requires every reported vulnerability to be
independently reproduced by the fuzzer/sanitizer before it counts. This directly answers
the single biggest failure mode in LLM-assisted security research: one cited study found
**70% of LLM-flagged crashes in an OSS-Fuzz-Gen benchmark were false positives** when not
held to this standard.

**Adopted as:** a hard gate in `04-triage-and-minimization-agent.md` and the
`vulnres-triage` agent — nothing enters `vuln_res/sweep-reports/` as an open finding without an
attached, re-runnable repro command and a captured tool-level signal (panic, ASan report,
hang timeout), never an agent's prose description alone. This is also why `plans/README.md`
already defines "PoC" as a minimized *input*, not a claim.

## 3. Human-gated verdicts above a severity threshold (agentpatterns.ai's triage pattern)

Even with fuzzer-confirmation, the recommended pattern lets an agent run the
discovery-and-triage loop unattended but requires a human to confirm the final verdict —
automation handles volume, a person handles judgment on anything that matters.

**Adopted as:** `05-disclosure-and-fix-agent.md`'s existing rule that every fix lands as an
ordinary human-reviewed PR stays; this adds that any finding scoring in the top tier of
`04`'s reachability × memory-safety × blast-radius rubric gets flagged for the user
directly, before `vulnres-disclosure` drafts anything — not just "eventually reviewed in
the PR queue."

## 4. Engineer PoC code like real software, and chain distinct bugs deliberately (Pwn2Own-caliber teams: NCC Group, Fox-IT, STAR Labs, ZDI)

Competition-grade exploit writeups converge on two habits worth borrowing even at our much
smaller scale: (a) exploit/PoC code is written, tested, and packaged with the same rigor as
production code — not a one-off throwaway script — because an unreliable PoC is worse than
no PoC; and (b) the highest-value findings are rarely one isolated bug — they're two or
more distinct, individually-unremarkable issues chained (e.g. STAR Labs' Pwn2Own Berlin
2025 hypervisor escape: a TOCTOU length-field re-read chained into a heap overflow; ZDI's
VMware Workstation chain: an uninitialized-variable bug chained with a stack overflow).

**Adopted as, with the scope line held exactly where `../CLAUDE.md` already draws it:**
when this suite's fuzzing produces more than one distinct, reachable bug in
**our own code or our own dependency graph**, the triage/exploit-dev stage should
deliberately check whether they compose — e.g. does the `img4.rs` parser bug plus a
`plan.rs` logic gap ever let a fuzzed-but-"valid" `BootState` drive `plan()` toward an
`IllegalTransition` that should have been rejected? That is legitimate, valuable
multi-step exploit-development *methodology* applied to code we own, and it is exactly how
a findings' real-world severity gets proven rather than guessed. It is never applied to
Apple's iBoot/SEP/Boot ROM as the target, real device or VM, regardless of how many
distinct issues a future pass might notice in the firmware sitting under `../research/` —
that line doesn't move because the methodology got more sophisticated.

## 5. MITRE ATT&CK as a classification lens, not an attack plan

ATT&CK's practical home in red-team practice is emulation planning against live
infrastructure — not directly applicable to fuzzing our own parser code. Its one genuinely
useful import here is as a **shared vocabulary for classifying what a VM/environment
hygiene finding actually represents**, when `vulnres-environment-runner` evaluates a
newly-spawned disposable VM or container's configuration (exposed services, default
credentials, stale permissions) rather than our source code — see
`03-sandboxed-execution-environment.md`'s "evaluating virtual environments" section. A
finding like "this disposable VM has an unauthenticated service listening on all
interfaces" is usefully tagged `T1133`-shaped ("External Remote Services") for triage
consistency, even though we're auditing an environment we built ourselves, not emulating
an adversary against someone else's.

## What this explicitly does not change

None of the above loosens `../CLAUDE.md`'s scope boundary. "Cutting-edge" and "novel" here
means: tool-equipped agents instead of guesswork, fuzzer-confirmed findings instead of
LLM-asserted ones, human-gated verdicts on anything severe, professionally-engineered PoCs,
and deliberate bug-chaining — all applied to `bputil-eval`'s own code and dependency graph,
executed only inside a disposable VM or container (see the updated "Execution posture" in
`../CLAUDE.md`), never against Apple's platform security, a real device, or this host.

## Sources

- [Google's Zero-Day Hunters Test AI for Security Research](https://www.bankinfosecurity.com/googles-zero-day-hunters-test-ai-for-security-research-a-25592)
- [Google's Project Naptime Aims for AI-Based Vulnerability Research](https://securityboulevard.com/2024/06/googles-project-naptime-aims-for-ai-based-vulnerability-research)
- [Project Zero — Vulnerability Disclosure FAQ](https://projectzero.google/vulnerability-disclosure-faq.html)
- [Project Zero — About PZ](https://projectzero.google/about-pz.html)
- [MITRE ATT&CK Framework Explained — Group-IB](https://www.group-ib.com/resources/knowledge-hub/mitre-attack-framework/)
- [How to Use ATT&CK for Red Teaming — InventiveHQ](https://inventivehq.com/blog/how-to-use-attack-for-red-teaming)
- [What is the MITRE ATT&CK Framework? — Expel](https://expel.com/cyberspeak/what-is-the-mitre-attack-framework/)
- [FuzzingBrain V2: A Multi-Agent LLM System for Automated Vulnerability Discovery and Reproduction (arXiv 2605.21779)](https://arxiv.org/abs/2605.21779)
- [PBFuzz: Agentic Directed Fuzzing for PoV Generation (arXiv 2512.04611)](https://arxiv.org/html/2512.04611)
- [Automated Crash Triage Pipeline for High-Volume Fuzzing](https://dev.to/beefedai/automated-crash-triage-pipeline-for-high-volume-fuzzing-4jp1)
- [Scaling Coverage-Guided Fuzzing in CI for Large Codebases](https://dev.to/beefedai/scaling-coverage-guided-fuzzing-in-ci-for-large-codebases-2472)
- [Agent-Driven Fuzzing with Human-Gated Crash Triage](https://agentpatterns.ai/workflows/agent-driven-fuzzing-human-gated-triage/)
- [Chainspotting 2 — Fox-IT / OffensiveCon 2025](https://www.fox-it.com/nl-en/chainspotting-2-the-unofficial-sequel-to-the-2018-talk-chainspotting-offensivecon-2025)
- [Lessons From Pwn2Own Berlin 2025: Building a Hypervisor Escape — STAR Labs](https://starlabs.sg/blog/2025/05-lessons-from-pwn2own-berlin-2025-building-a-hypervisor-escape/)
- [CVE-2023-20869/20870 — Exploiting VMware Workstation at Pwn2Own Vancouver — ZDI](https://www.thezdi.com/blog/2023/5/17/cve-2023-2086920870-exploiting-vmware-workstation-at-pwn2own-vancouver)
