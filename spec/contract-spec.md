bputil-eval — Contracts Specification
9 Nov 2026 · @Sunyata
A design-by-contract specification for bputil-eval. It states, as checkable predicates, the invariants the tool preserves, the validity rules for every data structure, and the preconditions and postconditions of every operation. It is the formal companion to the architecture and agent-specification documents.
Scope and conventions
This document specifies bputil-eval as a set of contracts in the design-by-contract sense: each operation has preconditions (what must hold before it runs), postconditions (what it guarantees on success), and declared error outcomes; the system has invariants that hold before and after every operation. A build agent implements these as assertions; an operate agent relies on them. Where this document and prose elsewhere differ, this document is authoritative on behaviour, and the agent-spec's golden rules remain authoritative on what is permitted.
Notation.
• requires = precondition; ensures = postcondition; raises = error outcome with its exit code.
• Predicates are written as named, checkable conditions, e.g. InOneTrueRecovery, SingleContainerTouched.
• s0 and s1 denote the BootState before and after an operation.
• Keywords MUST / MUST NOT / SHOULD / MAY follow RFC 2119, as in the agent spec.
• A contract that cannot be satisfied is a refusal, not a best effort: the operation does nothing and reports.
Relationship to the other documents. The architecture and implementation plan (companion doc, sections 9–10) define the components and commands; the agent specification defines who may invoke them and the binding rules; this document makes the behavioural guarantees precise enough to test. The three are consistent by construction: every golden rule appears here as an invariant or a precondition.
Global invariants
These predicates hold before and after every operation. Any operation that would falsify one MUST fail closed (exit 13, InvariantViolated) and change nothing further.
Invariant
Predicate
Rationale
ReadOnlyUnlessGated
No command that mutates state has run unless environment == OneTrueRecovery and a typed owner confirmation was recorded
The core safety property; mirrors golden rules 3 and 4
SingleContainerTouched
For any transition, exactly one target_volume_group differs between s0 and s1; all other_containers are byte-identical
Mirrors golden rule 5
Reversible
For every reachable non-Full state there exists a defined transition back to Full
Guarantees recovery; golden rule 5
NoCredentialHandling
The process never reads, stores, logs or transmits owner credentials; only Apple's tools prompt
Golden rule 4
SupportedMechanismsOnly
Every state change is attributable to a recorded bputil/kmutil/csrutil invocation
Golden rule 2
MeasuredTruth
Any asserted security state is backed by a BootState captured after the change
Golden rule 8
EvidenceComplete
After any session, the evidence bundle contains every invoked command, its exit code and output hash
Enables audit and disclosure
OwnershipConfirmed
No operation proceeds unless device ownership was confirmed at session start
Golden rule 1
ReadOnlyUnlessGated and SingleContainerTouched are the two the verifier checks most aggressively, because they are the ones whose failure would indicate either a tool bug or a flaw in Apple's enforcement. A failure of the latter kind is a disclosure finding, not a retryable condition.
Data contracts
Each structure is valid only if its predicate holds. A build agent validates on construction and on deserialisation; an invalid structure is an 11 (ParseError), never a guess.
Enumerations
• SecurityMode ∈ { Full, Reduced, Permissive, Unknown }.
• Environment ∈ { MacOS, OneTrueRecovery }.
• Signer ∈ { Apple, SEPLocalPolicy, Unknown }.
• ObjectRole ∈ { LLB, iBoot, KernelCache, AuxKC, CustomBootObject }.
• TargetProfile ∈ { Full, ReducedKexts, PermissiveCustomKernel }.
BootState
Field
Type
Constraint
schema_version
u32
> 0; equals the tool's current schema version
captured_at
RFC3339
not in the future
environment
Environment
present
host.chip / host.macos_build
string
non-empty
host.serial_masked
string
at most the last 4 characters; never the full serial
target_container.security_mode
SecurityMode
Unknown only when environment == MacOS and policy is unreadable
target_container.ssv_enabled
bool
if security_mode == Permissive then ssv_enabled == false
target_container.allows_custom_kernel
bool
true only if security_mode == Permissive
target_container.allows_third_party_kexts
bool
true only if security_mode ∈ {Reduced, Permissive}
enrolled_objects[]
list
every sha384 is 96 lowercase hex chars; a CustomBootObject has signer == SEPLocalPolicy
other_containers[]
list
disjoint volume_group_uuid from target_container
evidence.raw_outputs[]
list
each entry has a command, an exit code and a stdout_sha256
Validity predicate ValidBootState(s): all field constraints above hold, and the derived booleans (allows_*) are consistent with security_mode. An inconsistency (for example Permissive with ssv_enabled == true) is not clamped; it is a parse error, because it means the tool misread the device.
PlannedTransition
Field
Type
Constraint
from_mode
SecurityMode
equals the current BootState.security_mode
to_profile
TargetProfile
an allowed successor of from_mode (see the state diagram)
target_volume_group
string
equals the evaluated container
commands[]
list
non-empty for a mutating profile; each argv[0] ∈ {bputil, kmutil, csrutil}
requires
object
environment == OneTrueRecovery and owner_credentials == true for any mutating profile
invariants_to_check[]
list
includes SingleContainerTouched and the mode-specific postcondition
Validity predicate ValidPlan(p, s0): p.from_mode == s0.security_mode, p.to_profile is a permitted transition from p.from_mode, and every argv[0] is an allowed tool. A plan failing this is never executed.
Report
Field
Type
Constraint
baseline
BootState
ValidBootState
result
BootState or null
null iff the session was evaluate-only; else ValidBootState
diff[]
list
empty iff baseline and result are equal
invariants[]
list
one entry per global invariant, each with held: bool
exit_code
i32
∈ the defined exit-code set
evidence_bundle_path
string
points to an existing, hash-chained bundle
Validity predicate ValidReport(r): if exit_code == 0 then every invariants[].held == true and, for a mutating session, result reflects the planned to_profile. A Report with exit_code == 0 but any held == false is itself invalid and is treated as an InvariantViolated.
Operation contracts
Each operation lists requires, ensures and raises. Unlisted state is unchanged. All operations preserve every global invariant.
evaluate(volume) -> BootState
• requires: OwnershipConfirmed; the volume exists.
• ensures: returns s with ValidBootState(s); no system state changed (s1 == s0); a raw-output record for each tool invoked is in evidence.
• raises: 11 ParseError if a tool's output cannot be parsed; 14 UnsupportedHost if no parser covers the chip/build. Never 10, because it does not mutate.
plan(volume, target) -> PlannedTransition
• requires: a current BootState s0 for volume; target ∈ TargetProfile.
• ensures: returns p with ValidPlan(p, s0); p.commands is exactly the command set for (s0.security_mode -> target) and nothing more; for any mutating target, p.requires.environment == OneTrueRecovery. No system state changed.
• raises: 14 UnsupportedHost if the transition is undefined for this host; returns a dry-run plan even in macOS (planning is always read-only).
apply(plan) -> Report
• requires: InOneTrueRecovery; a recorded typed owner confirmation; ValidPlan(plan, evaluate(plan.target_volume_group)) still holds (re-checked against a fresh baseline).
• ensures (on exit 0): result.security_mode equals the mode implied by plan.to_profile; SingleContainerTouched holds; Reversible holds; a complete evidence bundle exists; every global invariant's held == true.
• raises: 10 PreconditionNotMet if not in 1TR or no confirmation — and then s1 == s0; 12 TransitionFailed if an Apple tool returns non-zero — baseline preserved, stderr reported; 13 InvariantViolated if the post-state check fails — halt, preserve evidence, recommend revert.
• side effects: runs exactly plan.commands, in order; nothing else.
verify(baseline, volume) -> Report
• requires: a baseline BootState.
• ensures: returns a Report whose diff is the exact difference between baseline and a fresh BootState, and whose invariants[] has one entry per global invariant with its held value; no system state changed.
• raises: 11 ParseError; 13 InvariantViolated if any invariant is false (the Report still returns, carrying the finding).
revert(volume) -> Report
• requires: InOneTrueRecovery; recorded owner confirmation.
• ensures (on exit 0): result.security_mode == Full; result.sip.status == Enabled; no CustomBootObject remains enrolled; SingleContainerTouched holds.
• raises: as apply.
report(session) -> path
• requires: a completed session.
• ensures: returns the path to a hash-chained evidence bundle satisfying EvidenceComplete; read-only.
• raises: 11 if the session record is incomplete.
The asymmetry is deliberate: evaluate, plan, verify and report can never return 10, because they never need 1TR; apply and revert always can, because they always do.
Internal safety-critical contracts
These four functions are where the global invariants are enforced. They are the highest-assurance part of the codebase and carry the most test weight.
env.is_mutation_allowed() -> bool
• ensures: returns true only if environment == OneTrueRecovery. The result is derived from the live environment, never cached across a reboot, never overridable by a flag or environment variable.
• contract for callers: apply and revert MUST call this and abort on false before any other work.
authorize.confirm() -> Confirmation
• requires: is_mutation_allowed() == true.
• ensures: returns a Confirmation only after an interactive, typed human acknowledgement of the specific PlannedTransition. Holds no secret. Does not prompt for or receive the owner password — that prompt belongs to Apple's tool, which runs later.
• MUST NOT: be satisfiable non-interactively, by a stored token, or by an agent.
execute.run(plan) -> RawResults
• requires: is_mutation_allowed(); a valid Confirmation for plan.
• ensures: executes exactly the entries of plan.commands, in order; each via the single audited wrapper; captures argv, exit code and output hash for every one. Executes nothing not in plan.commands.
• raises: stops at the first non-zero exit and returns what ran (12 TransitionFailed).
verify.assert_invariants(baseline, fresh) -> InvariantResults
• ensures: evaluates every global invariant against (baseline, fresh) and returns a result per invariant; marks the whole session 13 InvariantViolated if any is false. Pure function of its inputs, so it is exhaustively unit-testable.
• MUST: be called after every apply and revert, and its failure MUST NOT be swallowed.
Together these give a short, checkable chain: a mutation can occur only if is_mutation_allowed and a live Confirmation both hold, only the planned commands run, and the outcome is always re-measured. A build agent is expected to prove each of these contracts with a dedicated test, including negative tests that force each precondition false.
Protocol and sequence contracts
The operations compose under ordering rules. An agent or caller that violates the order gets a precondition failure, not undefined behaviour.
• Evaluate-before-plan. plan requires a current BootState; a caller MUST evaluate first, or plan derives one itself, but never plans against a stale state across a reboot.
• Plan-before-apply. apply consumes a PlannedTransition; it re-evaluates a fresh baseline and re-checks ValidPlan before executing, so a plan made in macOS cannot be applied against a device that changed in between.
• Baseline-before-mutate, verify-after-mutate. Every apply/revert captures a Full-or-current baseline before and runs verify after. A session with a mutation but no post-verification is itself an invariant violation.
• One transition per apply. A single apply performs one mode transition. Chained changes are separate, separately confirmed operations.
• Idempotent re-measurement. evaluate and verify may run any number of times with no effect beyond producing a state; they are safe to retry.
The security mode is a state machine, and the only legal transitions are those below; each edge's guard is the same conjunction, InOneTrueRecovery ∧ Confirmation. plan refuses any edge not in this machine.
Enforcement and traceability
Every contract maps to a place it is checked and a test that proves it. A contract with no enforcement point is a documentation defect.
Contract
Enforced in
Proven by
ReadOnlyUnlessGated
env.is_mutation_allowed, called by apply/revert
Negative test: apply in macOS returns 10, state unchanged
SingleContainerTouched
verify.assert_invariants
Round-trip test diffs all other_containers; must be identical
NoCredentialHandling
authorize.confirm holds no secret
Code review + test that no credential field exists; grep gate in CI
SupportedMechanismsOnly
execute.run via the one audited wrapper
Test: Executor rejects an argv whose argv[0] is not an allowed tool
ValidPlan
plan and re-checked in apply
Golden-file tests per profile; fuzz the planner inputs
MeasuredTruth
verify after every mutation
Test: a session that skips post-verify is rejected
Reversible
the state machine (revert defined from every state)
Round-trip tests for both non-Full states
EvidenceComplete
report
Schema test on the bundle; hash-chain verification
What a violation means. A failed contract is one of two things. If a precondition or a data predicate fails, it is a caller or input error, handled by the stated exit code. If a postcondition or global invariant fails after the tool did everything correctly — most seriously ReadOnlyUnlessGated or SingleContainerTouched — then either the tool has a bug or the platform did not enforce what it claims. The tool treats that as exit 13, preserves the full evidence bundle, recommends revert, and routes the finding to coordinated disclosure with Apple. It never continues as though the invariant held.
Traceability closes the loop. Each golden rule in the agent spec appears here as an invariant or precondition, each invariant has an enforcement point, and each enforcement point has a test. A reviewer can therefore follow any rule from the spec to the line of code that enforces it and the test that demonstrates it.
