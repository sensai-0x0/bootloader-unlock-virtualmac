bputil-eval — Phased Development Plan
9 Nov 2026 · @Sunyata
A comprehensive, gated plan to build the boot-policy evaluation tool and its control surface, implementing the architecture, agent specification and contracts specification already in this project. The ordering principle is that every unit of risk is deferred as late as possible: the read-only evaluator ships first and carries none, and each mutating capability is added only behind a passed safety gate.
Objectives and principles
What is being built. Two capabilities in one binary: a build/evaluation tool that measures a Mac's boot-chain trust state, and a control surface that helps a human owner carry out a supported security-policy change (Reduced Security for kexts, Permissive for a custom kernel) through Apple's bputil, kmutil and csrutil. The two share the BootState model, the planner and the evidence pipeline; they differ only in whether a step mutates.
Guiding principles.
1. Risk deferred to the latest possible phase. The read-only evaluator is built and shipped before any mutating code exists.
2. Every phase is gated. A phase ends with a concrete, testable exit gate; the next phase does not start until it passes.
3. Safety properties are enforced in code, not documents. Each contract from the contracts spec lands with its enforcement point and its test in the same phase.
4. Scratch containers before real ones. All mutation testing happens on a disposable APFS container, with full revert proven before any real use.
5. Evidence by default. Every run emits the reproducible bundle, so the project's own testing produces audit trails from day one.
Effort, not dates. Phases are sized in relative effort (S / M / L), because the calendar depends on team size and on access to the hardware matrix. A rough reading for one or two engineers is that P0–P1 is the first increment worth shipping, P2–P3 the second, and P4–P5 the third.
Phases at a glance
Six phases in two groups. The first three are read-only and ship incrementally; the last three add mutation, and none of them starts until the read-only path is proven. The diagram shows that split and the safety gate between the groups.
Phase
Goal
Effort
Mutating
Exit gate
P0 Foundations
Repo, CI, fixtures harness, IMG4 parser spike, the single audited command wrapper
S
No
CI green; the wrapper records argv, exit code and output hash for every call
P1 Evaluator
evaluate and report: build and serialise BootState
M
No
Runs on fixtures and a real Mac; evaluate twice differs only in timestamp
P2 Planner
Profiles, PlannedTransition, dry-run plan
S
No
Golden-file plans correct per profile; invalid plans rejected
P3 Executor + Verifier
authorize, execute, verify; full → reduced → full on a scratch container
L
Yes
Round trip verified; negative tests force each precondition false
P4 Permissive + Control
Custom-kernel enrolment, revert, and the control surface for a human/operate agent
L
Yes
full → permissive → full verified; control surface honours the autonomy boundary
P5 Hardening + Release
Per-generation fixtures, parser fuzzing, signed reproducible bundle, docs, release
M
No
Release criteria met; coverage across the hardware matrix
The gate between P2 and P3 is the one that matters most: no mutating code runs until the read-only path is demonstrably side-effect-free and the audited wrapper is the only route to a subprocess.
Phase 0 — Foundations
Goal. Put the repo, CI and the safety-critical plumbing in place before any feature, so that every later line of code sits on an audited base.
Workstreams.
• Repo and toolchain. Rust project targeting a static binary; formatter, linter (clippy), and a reproducible build.
• The single audited command wrapper. The one function through which every subprocess runs; it records argv, exit code and an output hash. No module may call std::process directly.
• IMG4 parser spike. Integrate a vetted img4 library behind an isolated FFI boundary and prove it parses a public IPSW manifest.
• Fixtures harness. Capture real bputil -d, csrutil status, nvram -p and ioreg output into tests/fixtures for deterministic parser tests.
• CI. Build, test, clippy, plus two guard checks: fail the build if std::process is used outside the wrapper, or if any credential-shaped field is introduced.
Deliverables. Skeleton binary, CI pipeline, the wrapper with tests, the IMG4 spike, an initial fixture set.
Exit gate. CI is green; the wrapper demonstrably records every call; the no-direct-subprocess and no-credential-field guards pass. Nothing mutates yet.
Phase 1 — Read-only evaluator
Goal. Deliver a standalone, shippable evaluator. This is the first increment with user value and it carries no risk, because it only reads.
Workstreams.
• state/collect. Invoke the Apple tools through the wrapper and parse their output into a BootState.
• state/img4. Fold manifest hashes and signers into enrolled_objects.
• BootState type. Serde serialisation and the ValidBootState predicate, so an inconsistent reading is a parse error, not a guess.
• env detection. macOS vs 1TR, chip, macOS build.
• report. The hash-chained evidence bundle writer.
Deliverables. The evaluate and report subcommands, --json output, and fixture-based unit tests covering each parser.
Exit gate. Runs on a real Mac in macOS and against fixtures; running evaluate twice differs only in the timestamp (the read-only proof); ValidBootState is enforced. Tag this as the first shippable release (v0.1): a reproducible boot-state evaluator is useful on its own, independent of any unlock capability.
Phase 2 — Planner and diff
Goal. Turn a desired target into an executable plan, as data, while still changing nothing.
Workstreams.
• Profiles. full, reduced-kexts, permissive-custom-kernel.
• plan. Diff the current BootState against the target and emit a PlannedTransition: the exact commands, the consequences (SSV off, SIP change, SKP re-seal), the requires block, and the invariants to check afterward.
• state/diff. A structured BootState difference used by both plan and verify.
• ValidPlan enforcement. Refuse any transition not in the security-mode state machine from the contracts spec.
Deliverables. The plan --target subcommand and golden-file tests fixing the command set per profile.
Exit gate. Plans are correct for every profile; invalid plans and edges outside the state machine are rejected; still zero mutation. An operator can now read exactly what would run before anyone touches 1TR.
Phase 3 — Executor, authoriser, verifier
Goal. Introduce mutation for the first time, behind the full safety plumbing, on a disposable container only.
Workstreams.
• env.is_mutation_allowed. The 1TR gate, derived live, never cached across a reboot, never overridable.
• authorize.confirm. Interactive, typed confirmation of the specific plan; holds no secret and cannot be satisfied non-interactively.
• execute.run. Runs exactly plan.commands through the audited wrapper, and nothing else.
• verify.assert_invariants. Re-measures and asserts every global invariant; a pure function, exhaustively testable.
• The full → reduced → full round trip on a scratch APFS container.
Deliverables. The apply and verify subcommands; the round trip working end to end on a scratch container.
Exit gate. The round trip verifies; the negative tests all pass — apply in macOS returns 10 and changes nothing, the executor rejects any argv not in the plan, and a deliberately wrong post-state is caught as 13. The safety contracts are enforced in code, with tests, not just documented. Choosing the least-invasive round trip first means the riskiest plumbing is exercised before the Permissive path is added.
Phase 4 — Permissive path, revert, and control surface
Goal. Add the custom-kernel path and the revert, and build the control surface that an operate agent or a human drives — the half of the tool that actually carries out an unlock.
Workstreams.
• Permissive enrolment. Set Permissive for the target container and enrol a custom boot object via kmutil configure-boot, with the result verified as signer == SEPLocalPolicy and ssv_enabled == false.
• revert. The full pipeline back to Full Security, with SIP re-enabled and the custom object dropped.
• Control surface. The operate flow: evaluate → plan run autonomously, then the hand-off where the human reboots to 1TR and authenticates, then apply → verify. It presents the plan, consequences and requires verbatim, and it never touches credentials or simulates the reboot.
• The full → permissive → full round trip on a scratch container.
Deliverables. The revert subcommand, Permissive support, and the control surface (interactive prompts plus a JSON mode an operate agent consumes).
Exit gate. The Permissive round trip verifies; the control surface routes every credential and 1TR step to the human; the autonomy-boundary tests pass (an agent-driven run cannot reach apply without the human gate). This is the first point at which the tool can perform a real unlock, and only on a device whose owner is present.
Phase 5 — Hardening and release
Goal. Take the working tool to production quality and a signed release.
Workstreams.
• Coverage across the hardware matrix. Fixtures and a verified round trip per chip generation and macOS build in scope.
• Fuzzing. Fuzz the bputil, csrutil and IMG4 parsers against malformed input, since parsing untrusted-shaped text is the main memory-safety surface.
• Reproducible evidence bundle. Finalise the signed, hash-chained bundle and a standalone verifier.
• Documentation. Man pages, an operator guide, and the disclosure policy for any exit-13 finding.
• Release. Versioning, binary signing and distribution.
Deliverables. v1.0, complete docs, a fuzz corpus, and signed release artifacts.
Exit gate. Coverage across the hardware matrix; fuzzing clean within an agreed budget; the reproducible bundle independently verified; documentation complete, including the disclosure path. After this, new chip generations are an incremental fixtures-and-parser update, not a new project.
Cross-cutting concerns
Testing strategy. Five layers, each tied to a phase: unit tests against fixtures (P0–P1), golden-file tests for plans (P2), round-trip tests on scratch containers (P3–P4), negative and safety tests that force each precondition false (P3 onward), and fuzzing of the parsers (P5). Every test run emits an evidence bundle, so the suite also exercises the audit path.
CI gates. On every change: build, clippy, and the fixture tests, plus three standing guards — no std::process call outside the audited wrapper, no credential-shaped field anywhere, and a test proving that no mutating path is reachable without is_mutation_allowed() returning true. A red guard blocks merge.
Hardware test matrix. At least one base chip per generation in scope (M1–M5), a Pro or Max for the multi-die cases, each on the macOS builds being supported, each with a dedicated scratch container. Mutating tests never run on a primary machine.
Safety gates that block a mutating phase. Four conditions must hold before P3 begins and must stay true thereafter:
1. The read-only path is proven side-effect-free (evaluate twice differs only in timestamp).
2. The audited wrapper is the only route to a subprocess.
3. authorize.confirm cannot be satisfied non-interactively.
4. verify runs after every mutation and its failure cannot be swallowed.
If any of these regresses, mutating features are disabled until it is restored.
Risks and mitigations
Risk
Likelihood
Impact
Mitigation
bputil/kmutil flags drift across macOS builds
High
Medium
Read bputil -h at runtime; per-build fixtures; on an unknown host return 14 UnsupportedHost, never a guessed command
A scratch-container mistake bricks a test Mac
Low
High
DFU-restore runbook; never test on a primary machine; prove revert in P3 before the Permissive path in P4
Limited access to the hardware matrix
Medium
Medium
Prioritise owned generations; accept community-contributed fixtures; mark a host unsupported rather than guess
An invariant violation exposes a real Apple enforcement flaw
Low
High
Coordinated disclosure path; halt-and-preserve on exit 13; the finding is reported, never weaponised
An operate agent oversteps the autonomy boundary
Medium
High
Boundary enforced in code (no credential handling, live 1TR gate); autonomy-boundary tests; control surface refuses to proceed
Memory-safety bug in the IMG4 FFI
Low
Medium
Isolate unsafe at the FFI boundary; fuzz; use a vetted library
Scope creep toward exploitation
Low
High
The agent spec's out-of-scope list is binding; capability requests are answered by explaining the boundary, not partial compliance
The two high-impact rows to watch are the test-hardware mistake and the autonomy-boundary overstep; both are addressed by sequencing (revert before Permissive) and by enforcing the limits in code rather than in guidance.
